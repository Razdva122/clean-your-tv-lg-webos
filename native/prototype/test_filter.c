#include "filter.h"
#include <assert.h>
#include <stdio.h>
static int event(struct filter*f,unsigned code,int value,uint64_t now){struct ev e={0,0,1,code,value};return filter_event(f,&e,now);}
static int tap(struct filter*f,uint64_t now){assert(event(f,773,1,now)==OPEN_HOME);return event(f,773,0,now+100);}
int main(void){
 struct filter f={0};struct ev e={0,0,1,773,1};assert(sizeof e==16);
 assert(tap(&f,100)==DROP);assert(tap(&f,400)==DROP);assert(tap(&f,700)==RELEASE);
 f=(struct filter){0};assert(event(&f,773,1,100)==OPEN_HOME);
 assert(!filter_timeout(&f,2100));assert(event(&f,773,0,2200)==DROP);
 assert(tap(&f,2300)==DROP);assert(tap(&f,2600)==DROP);
 f=(struct filter){0};tap(&f,100);tap(&f,400);assert(tap(&f,2101)==DROP);
 f=(struct filter){0};tap(&f,100);tap(&f,400);assert(tap(&f,2000)==RELEASE);
 f=(struct filter){0};tap(&f,100);event(&f,773,1,400);event(&f,773,2,450);event(&f,773,0,500);assert(tap(&f,700)==DROP);assert(tap(&f,1000)==DROP);
 f=(struct filter){0};tap(&f,100);event(&f,28,1,300);assert(tap(&f,400)==DROP);assert(tap(&f,700)==DROP);
 f=(struct filter){0};tap(&f,100);assert(event(&f,1198,1,300)==PASS);tap(&f,400);assert(tap(&f,700)==RELEASE);
 f=(struct filter){0};tap(&f,100);event(&f,773,0,300);assert(tap(&f,400)==DROP);assert(tap(&f,700)==DROP);
 f=(struct filter){0};tap(&f,100);event(&f,773,1,400);assert(event(&f,773,1,410)==DROP);event(&f,773,0,510);assert(tap(&f,700)==DROP);
 f=(struct filter){0};event(&f,773,1,100);event(&f,773,0,139);assert(tap(&f,400)==DROP);assert(tap(&f,700)==DROP);
 f=(struct filter){0};tap(&f,1000);tap(&f,1300);assert(tap(&f,100)==DROP);
 f=(struct filter){0};assert(event(&f,412,1,100)==PASS);
 assert(!filter_timeout(&f,1299));assert(filter_timeout(&f,1300)==OPEN_LG);
 assert(!filter_timeout(&f,1500));assert(event(&f,412,0,1600)==PASS);
 assert(event(&f,412,1,2000)==PASS);assert(event(&f,412,0,2100)==PASS);assert(!filter_timeout(&f,4000));
 f=(struct filter){0};f.disabled=1;assert(event(&f,773,1,100)==PASS);assert(event(&f,773,0,200)==PASS);
 unsigned codes[]={28,103,105,106,108,412,114,115,116,1198,1199,2,398};
 for(unsigned i=0;i<sizeof codes/sizeof codes[0];i++)for(int v=0;v<3;v++)assert(event(&f,codes[i],v,6000)==PASS);
 e.type=3;assert(filter_event(&f,&e,6000)==PASS);
 e.type=2;e.code=8;assert(filter_event(&f,&e,6000)==PASS);
 e.type=0;e.code=0;assert(filter_event(&f,&e,6000)==PASS);
 e.code=3;assert(filter_event(&f,&e,6000)==RELEASE);
 puts("PASS: triple Home, timing, holds, repeats, interruption, cursor, other input, overflow");
}
