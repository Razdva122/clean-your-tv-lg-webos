"""Removal-only adapter for the immutable Developer Mode observer."""
from .no_root_observer import PROGRAM

# Run trusted helpers in the same TV process as the guarded mutation. The
# retained observer is read only to authenticate its original plan binding.
SOURCE = PROGRAM.replace(
    "var input=JSON.parse(process.argv[process.argv.length-1]), plan=input.plan;",
    "var input=cancellationInput, plan=input.plan;"
).replace("var result;\nswitch(input.command){", r"""
function cancel(){
 var goal=input.goal, fence='cancel-removal.json', prepared=opdir+'/reservation';
 if(plan.action!=='install'||!/^[a-f0-9]{32}$/.test(goal))fail('invalid-cancellation');
 if(!exists(opdir)||!exists(opdir+'/prepared.json'))return {};
 var inActive=exists(active+'/'+marker)||exists(active+'/'+fence);
 if(!inActive&&!exists(prepared)&&!exists(opdir+'/closed.json')){
  // The old reservation is absent. Read only this original operation's
  // effects, if it was able to submit anything.
  if(!plan.slots.some(function(s,i){return exists(claimName(i));}))return {};
 }
 var identity=checked(), closure=closed(), dir=inActive?active:exists(prepared)?prepared:null;
 if(!dir)return input.finalizing?{}:effects(closure);
 var pinned=directory(dir,true);
 if(pinned.dev!==identity.dev||pinned.ino!==identity.ino)fail('foreign-reservation');
 var expected=binding();expected.goal=goal;expected.nonce=identity.nonce;expected.dev=identity.dev;expected.ino=identity.ino;
 var tmp=opdir+'/.cancel-'+goal;
 function check(name){
  if(!same(pinned,directory(name,true))||!same(pinned,fs.statSync('.')))fail('changed-reservation');
  var names=fs.readdirSync('.'), owner=names.indexOf(marker)>=0, marked=names.indexOf(fence)>=0;
  if(names.length!==Number(owner)+Number(marked)||!marked&&!owner||
      !owner&&!closure&&!input.finalizing)fail('foreign-reservation');
  if(owner&&bound(json(name+'/'+marker)).nonce!==identity.nonce)fail('foreign-reservation');
  if(marked){
   // Recover the extra link if the previous process died during publication.
   var leaf=fs.lstatSync(fence);
   if(leaf.nlink===2&&exists(tmp)&&same(leaf,fs.lstatSync(tmp))){
    fs.unlinkSync(tmp);sync(opdir);
   }
   if(canonical(json(name+'/'+fence))!==canonical(expected))fail('foreign-reservation');
  }
  return {owner:owner,marked:marked};
 }
 var prior=process.cwd(), fd=fs.openSync(dir,c.O_RDONLY|c.O_DIRECTORY|c.O_NOFOLLOW), result;
 try{
  if(!same(pinned,fs.fstatSync(fd)))fail('changed-reservation');
  process.chdir(dir);
  var state=check(dir);
  if(!state.marked){
   if(input.finalizing)fail('foreign-reservation');
   // Publish complete bytes without an intermediate child in the reservation.
   if(exists(tmp)){
    var staging=fs.lstatSync(tmp);
    if(!staging.isFile()||staging.uid!==uid||staging.nlink!==1||(staging.mode&511)!==384)fail('changed-cancellation');
    fs.unlinkSync(tmp);
    exclusive(tmp,canonical(expected));
   }else exclusive(tmp,canonical(expected));
   check(dir);fs.linkSync(tmp,fence);fs.fsyncSync(fd);
   fs.unlinkSync(tmp);sync(opdir);
  }
  if(dir===prepared){
   if(exists(active)&&fs.readdirSync(active).length)fail('foreign-reservation');
   // A competing prepare can win this rename. Its nonempty directory cannot
   // be replaced. An old prepare may already have moved our pinned inode.
   try{fs.renameSync(prepared,active);}catch(e){if(e.code!=='ENOENT')throw e;}
   dir=active;sync(root);sync(opdir);
  }
  state=check(dir);if(!state.marked)fail('foreign-reservation');
  result=input.finalizing?{}:effects(closure);
  result.reservation={dev:identity.dev,ino:identity.ino};
  if(input.retire){
   if(!input.finalizing)fail('invalid-cancellation');
   if(state.owner){fs.unlinkSync(marker);fs.fsyncSync(fd);}
   check(dir);fs.unlinkSync(fence);fs.fsyncSync(fd);
  }
 }finally{process.chdir(prior);fs.closeSync(fd);}
 if(input.retire){
  try{fs.rmdirSync(dir);}catch(e){if(['ENOENT','ENOTEMPTY','EEXIST'].indexOf(e.code)<0)throw e;}
  sync(root);result.reservation=null;
 }
 return result;
}
function effects(closure){
 if(closure)return {};
 var unresolved=plan.slots.some(function(slot,i){
  var claim=evidence(i,'claim'), terminal=evidence(i,'terminal');
  return claim&&claim.disposition==='request'&&(!terminal||Object.keys(terminal.reply||{}).length===0||
    ['success','failure'].indexOf(terminal.terminal)<0);
 });
 return {package_pending:unresolved, eim_pending:configState('eim')==='unknown',
         launch_pending:configState('launch')==='unknown'};
}
try{return cancel();}catch(e){
 // A real staged reservation can still be promoted by an old process.
 // Unreadable operation history by itself does not establish such a writer.
 try{e.cancelReservation=exists(opdir+'/reservation');}catch(ignored){}
 throw e;
}
var result;
switch(input.command){
""")
