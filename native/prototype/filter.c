#include "filter.h"
int filter_event(struct filter*f,const struct ev*e,uint64_t now){
 if(e->type==0&&e->code==3)return RELEASE;
 if(e->type!=1)return PASS;
 if(now<f->last){f->home=0;f->short_press=0;f->count=0;}
 f->last=now;
 /* Cursor-show notifications are not physical button presses. */
 if(e->code==1198)return PASS;
 if(e->code==773&&f->disabled)return PASS;
 if(e->code!=773){if(e->value){f->short_press=0;f->count=0;}return PASS;}
 if(e->value==1){
  int held=f->home;
  if(held)f->count=0;
  f->home=1;f->short_press=1;f->since=now;
  return held?DROP:OPEN_HOME;
 }
 if(e->value==2){f->short_press=0;f->count=0;return DROP;}
 if(e->value==0){
  int valid=f->home&&f->short_press&&now-f->since>=40&&now-f->since<=500;
  f->home=0;f->short_press=0;
  if(!valid){f->count=0;return DROP;}
  int kept=0;
  for(int i=0;i<f->count;i++)if(now-f->taps[i]<=2000)f->taps[kept++]=f->taps[i];
  f->taps[kept++]=f->since;f->count=kept;
  if(kept==3){f->count=0;return RELEASE;}
 }
 return DROP;
}
