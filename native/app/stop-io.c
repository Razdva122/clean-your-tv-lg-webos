#define _DARWIN_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#include "private-io.h"
#include "stop-fs.h"
#include <errno.h>
#include <signal.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#if defined(CYTV_STOP_IO_BINDING_HEADER) && !defined(CYTV_STOP_IO_TEST_BUILD)
#error "Fixture binding requires explicit HOST test build"
#endif
#ifdef CYTV_STOP_IO_TEST_BUILD
#ifndef CYTV_STOP_IO_BINDING_HEADER
#error "HOST broker requires trusted fixture binding"
#endif
#include CYTV_STOP_IO_BINDING_HEADER
#endif

#define HEADER 16u
#define RESPONSE_CAP (1048576u + 4096u)
enum { READY=0, BEGIN=1, READ=2, SCAN=3, APPEND=4, END=5, CLOSE=6, PUBLISH=7 };

static int trusted_bindings(struct cytv_private_binding *private, struct cytv_stop_binding *stop)
{
#ifdef CYTV_STOP_IO_TEST_BUILD
    *private = host_private;
    *stop = host_stop;
    return 1;
#else
    /* Provisioning source is not implemented. Never discover trust by stat,
     * argv, environment, Node request or a file inside the admitted directory. */
    memset(private, 0, sizeof(*private));
    memset(stop, 0, sizeof(*stop));
    return 0;
#endif
}
static uint32_t get32(const unsigned char *p)
{ return (uint32_t)p[0]<<24 | (uint32_t)p[1]<<16 | (uint32_t)p[2]<<8 | p[3]; }
static void put32(unsigned char *p, uint32_t n)
{ p[0]=(unsigned char)(n>>24);p[1]=(unsigned char)(n>>16);p[2]=(unsigned char)(n>>8);p[3]=(unsigned char)n; }
static int read_exact(unsigned char *p, size_t size)
{
    size_t used=0;
    while(used<size) {
        ssize_t n=read(STDIN_FILENO,p+used,size-used);
        if(n<0&&errno==EINTR)continue;
        if(n<0)return -1;
        if(!n)return used?-1:0;
        used+=(size_t)n;
    }
    return 1;
}
static int write_exact(const unsigned char *p,size_t size)
{
    size_t used=0;
    while(used<size) {
        ssize_t n=write(STDOUT_FILENO,p+used,size-used);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)return 0;
        used+=(size_t)n;
    }
    return 1;
}
static int reply(unsigned op,uint32_t id,enum cytv_private_status status,const unsigned char *body,size_t len)
{
    if(len>RESPONSE_CAP)return 0;
    unsigned char header[HEADER]={'C','Y','I','1',0,0,0,0,0,0,0,0,0,0,0,0};
    header[4]=(unsigned char)op;header[5]=(unsigned char)status;
    put32(header+8,id);put32(header+12,(uint32_t)len);
    return write_exact(header,sizeof(header))&&write_exact(body,len);
}
static int read_reply(struct cytv_private_tx *tx,uint32_t id)
{
    struct cytv_journal_view view;
    enum cytv_private_status s=cytv_journal_read(tx,&view);
    if(s!=CYTV_PRIVATE_OK)return reply(READ,id,s,NULL,0);
    size_t len=4;
    for(size_t i=0;i<view.count;i++)len+=8+view.records[i].len;
    if(view.count>64||len>RESPONSE_CAP)return 0;
    unsigned char *raw=malloc(len);
    if(!raw)return reply(READ,id,CYTV_PRIVATE_UNKNOWN,NULL,0);
    put32(raw,(uint32_t)view.count);size_t offset=4;
    for(size_t i=0;i<view.count;i++) {
        put32(raw+offset,view.records[i].seq);put32(raw+offset+4,(uint32_t)view.records[i].len);
        memcpy(raw+offset+8,view.records[i].raw,view.records[i].len);
        offset+=8+view.records[i].len;
    }
    int ok=reply(READ,id,CYTV_PRIVATE_OK,raw,len);
    free(raw);return ok;
}
int main(int argc,char **argv)
{
    if(argc!=2||strcmp(argv[1],"controller"))return 2;
    (void)signal(SIGPIPE,SIG_IGN);
    struct cytv_private_binding binding;
    struct cytv_stop_binding stop;
    struct cytv_lease *lease=NULL;
    struct cytv_private_tx *tx=NULL;
    if(!trusted_bindings(&binding,&stop)) {
        (void)reply(READY,0,CYTV_PRIVATE_UNKNOWN,NULL,0);return 1;
    }
    enum cytv_private_status s=cytv_lease_acquire(&binding,&lease);
    if(!reply(READY,0,s,NULL,0)||s!=CYTV_PRIVATE_OK) {
        if(lease)(void)cytv_lease_close(&lease);
        return 1;
    }
    uint32_t expected=1;
    int result=0;
    for(;;) {
        unsigned char header[HEADER];
        int received=read_exact(header,sizeof(header));
        if(!received)break;
        if(received<0||memcmp(header,"CYI1",4)||header[5]||header[6]||header[7]||
           !expected||get32(header+8)!=expected||get32(header+12)!=0) {result=2;break;}
        unsigned op=header[4];uint32_t id=expected++;
        int ok=0;
        if(op==BEGIN) {
            s=cytv_tx_begin(lease,&tx);ok=reply(op,id,s,NULL,0);
        } else if(op==READ&&tx) ok=read_reply(tx,id);
        else if(op==END&&tx) {
            s=cytv_tx_end(&tx);ok=reply(op,id,s,NULL,0);
        } else if(op==CLOSE&&!tx) {
            s=cytv_lease_close(&lease);
            result=reply(op,id,s,NULL,0)&&s==CYTV_PRIVATE_OK?0:2;
            break;
        } else {result=2;break;}
        if(!ok){result=2;break;}
    }
    /* EOF is observed only AFTER any synchronous operation/response drains.
     * No signal handler closes a live native operation's FDs. */
    if(tx&&cytv_tx_end(&tx)!=CYTV_PRIVATE_OK)result=2;
    if(lease&&cytv_lease_close(&lease)!=CYTV_PRIVATE_OK)result=2;
    return result;
}
