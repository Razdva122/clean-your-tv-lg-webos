#include <stdint.h>
struct ev {uint32_t sec,usec;uint16_t type,code;int32_t value;};
struct filter {int home,short_press,count,disabled;uint64_t since,last,taps[3];};
enum action {PASS,OPEN_HOME,DROP,RELEASE};
int filter_event(struct filter*,const struct ev*,uint64_t);
