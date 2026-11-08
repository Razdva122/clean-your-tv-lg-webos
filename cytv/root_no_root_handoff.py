"""Transfer an inert Root removal fence to the exact No-root observer plan.

The outer wrapper is not the immutable observer capsule source. Both it and
detached package workers retain the original native Root locks until exit.
"""
import hashlib
import json
import re
import shlex
import time
import uuid

from .errors import UserError, TVCommandError
from .root_clean_tail import gate_bytes


def refuse():
    raise UserError('The original No-root operation cannot safely continue. Recovery data was kept.', reason_code='pending-operation')


def validate(stamp):
    if (type(stamp) is not dict or set(stamp) != {'operation', 'removal', 'lease'}
            or any(type(value) is not str or not re.fullmatch('[a-f0-9]{32}', value) for value in stamp.values())):
        refuse()
    return stamp


def support(installer):
    version=installer.tv_info.get('node_version')
    if not version:
        version=installer.remote.run('/usr/bin/node --version').strip().lstrip('v')
    match=re.fullmatch(r'(\d+)\.(\d+)\.(\d+)',version)
    if not match:refuse()
    bundle=installer.payload/'root-updater'
    if int(match[1]) < 8:
        if tuple(map(int,match.groups())) != (0,12,2):refuse()
        bundle=installer.payload/'legacy-root-beta/root-updater'
    path=bundle/'cleanup_tail.js'
    try:
        raw=path.read_bytes()
        files=json.loads((bundle/'bundle.json').read_text())['files']
        if (any(p.is_symlink() for p in (path,*path.parents))
                or hashlib.sha256(raw).hexdigest()!=files['cleanup_tail.js']):refuse()
        gate,_=gate_bytes(installer)
        return raw.decode('utf8'),gate
    except (OSError,ValueError,KeyError,TypeError):refuse()


PROGRAM = r'''
(function () {
  'use strict';
  var fs = require('fs'),
    C = require('constants'),
    cp = require('child_process'),
    crypto = require('crypto'),
    vm = require('vm');
  function emptyBuffer(size) {
    return Buffer.alloc ? Buffer.alloc(size) : new Buffer(size);
  }
  function textBuffer(text) {
    return Buffer.from ? Buffer.from(text) : new Buffer(text);
  }
  var input = JSON.parse(process.argv[process.argv.length - 1]),
    root = '/var/lib/clean-your-tv-installation';
  if (input.cleanup_stdin) {
    var chunks = [],
      length = 0,
      buffer = emptyBuffer(65536),
      count;
    while ((count = fs.readSync(0, buffer, 0, buffer.length, null)) > 0) {
      length += count;
      if (length > 1048576) throw Error('oversized-cleanup-support');
      var chunk = emptyBuffer(count);
      buffer.copy(chunk, 0, 0, count);
      chunks.push(chunk);
    }
    input.cleanup = Buffer.concat(chunks).toString('utf8');
  }
  function fail() {
    throw Error('root-successor-ownership-required');
  }
  function object(v) {
    return v && typeof v === 'object' && !Array.isArray(v);
  }
  function canonical(v) {
    if (Array.isArray(v)) return '[' + v.map(canonical).join(',') + ']';
    if (object(v))
      return (
        '{' +
        Object.keys(v)
          .sort()
          .map(function (k) {
            return JSON.stringify(k) + ':' + canonical(v[k]);
          })
          .join(',') +
        '}'
      );
    return JSON.stringify(v);
  }
  function sha(v) {
    return crypto.createHash('sha256').update(v).digest('hex');
  }
  function at(fd, name) {
    return '/proc/self/fd/' + fd + (name ? '/' + name : '');
  }
  function owned(s, dir) {
    if (
      s.uid !== 0 ||
      s.mode & 18 ||
      (dir ? !s.isDirectory() : !s.isFile() || s.nlink !== 1)
    )
      fail();
  }
  var fds = [];
  function directory(path) {
    var fd = fs.openSync('/', C.O_RDONLY | C.O_DIRECTORY | C.O_NOFOLLOW);
    fds.push(fd);
    path
      .split('/')
      .filter(Boolean)
      .forEach(function (name) {
        fd = fs.openSync(
          at(fd, name),
          C.O_RDONLY | C.O_DIRECTORY | C.O_NOFOLLOW
        );
        fds.push(fd);
        var s = fs.fstatSync(fd);
        if (!s.isDirectory() || s.uid !== 0 || (s.mode & 18 && !(s.mode & 512)))
          fail();
      });
    owned(fs.fstatSync(fd), true);
    return fd;
  }
  function bytes(file, size) {
    var raw = emptyBuffer(size),
      offset = 0;
    while (offset < size) {
      var count = fs.readSync(file, raw, offset, size - offset, offset);
      if (count <= 0) fail();
      offset += count;
    }
    if (fs.fstatSync(file).size !== size) fail();
    return raw;
  }
  function read(fd, name) {
    var file = fs.openSync(
      at(fd, name),
      C.O_RDONLY | C.O_NOFOLLOW | C.O_NONBLOCK
    );
    try {
      var s = fs.fstatSync(file);
      owned(s, false);
      if (s.size > 4194304) fail();
      return JSON.parse(bytes(file, s.size).toString());
    } finally {
      fs.closeSync(file);
    }
  }
  function write(fd, name, value) {
    var temp = '.no-root-' + crypto.randomBytes(16).toString('hex'),
      file = fs.openSync(
        at(fd, temp),
        C.O_WRONLY | C.O_CREAT | C.O_EXCL | C.O_NOFOLLOW,
        384
      );
    try {
      var raw = textBuffer(canonical(value)),
        offset = 0;
      while (offset < raw.length) {
        var count = fs.writeSync(file, raw, offset, raw.length - offset, null);
        if (count <= 0) fail();
        offset += count;
      }
      fs.fsyncSync(file);
    } finally {
      fs.closeSync(file);
    }
    fs.renameSync(at(fd, temp), at(fd, name));
    fs.fsyncSync(fd);
  }
  function same(a, b) {
    return a.dev === b.dev && a.ino === b.ino;
  }
  function stamp(v) {
    if (
      !object(v) ||
      Object.keys(v).sort().join(',') !== 'lease,operation,removal' ||
      Object.keys(v).some(function (k) {
        return typeof v[k] !== 'string' || !/^[a-f0-9]{32}$/.test(v[k]);
      })
    )
      fail();
    return v;
  }
  if (process.getuid() !== 0) fail();
  var dir = directory(root),
    lock = fs.fstatSync(3),
    worker = fs.fstatSync(5);
  owned(lock, false);
  owned(worker, false);
  if (
    !same(lock, fs.lstatSync(at(dir, 'ownership.lock'))) ||
    !same(worker, fs.lstatSync(at(dir, 'worker.lock')))
  )
    fail();
  if (input.stage) {
    if (
      !/^\/tmp\/cytv-root-tail-[a-f0-9]{32}$/.test(input.stage) ||
      !/^[a-f0-9]{64}$/.test(input.gate_sha256)
    )
      fail();
    var staged = directory(input.stage),
      names = fs.readdirSync(at(staged));
    if (names.length !== 1 || names[0] !== 'gate') fail();
    var executable = fs.openSync(
        at(staged, 'gate'),
        C.O_RDONLY | C.O_NOFOLLOW | C.O_NONBLOCK
      ),
      info = fs.fstatSync(executable);
    owned(info, false);
    if (
      (info.mode & 4095) !== 493 ||
      info.size > 1048576 ||
      sha(bytes(executable, info.size)) !== input.gate_sha256 ||
      !same(info, fs.lstatSync(at(staged, 'gate')))
    )
      fail();
    fs.closeSync(executable);
    fs.unlinkSync(at(staged, 'gate'));
    fs.fsyncSync(staged);
    if (!same(fs.fstatSync(staged), fs.lstatSync(input.stage))) fail();
    fs.rmdirSync(input.stage);
  }
  var lease = read(dir, 'operation.json');
  if (
    !object(lease) ||
    Object.keys(lease).sort().join(',') !==
      'id,journal,owner,schema,stage,terminal' ||
    lease.schema !== 1 ||
    lease.terminal !== false ||
    !/^[a-f0-9]{32}$/.test(lease.id)
  )
    fail();
  var binding = null,
    original = null;
  if (lease.owner === 'clean-removal') {
    var match = /^product-([a-f0-9]{32})\.json$/.exec(lease.journal);
    if (!match || lease.stage !== 'verified-clean') fail();
    var record = read(dir, 'clean-removal-' + match[1] + '.json');
    original = stamp({
      operation: match[1],
      removal: record.removal,
      lease: lease.id
    });
  } else if (lease.owner === 'no-root') {
    if (
      !/^no-root-[a-f0-9]{32}\.json$/.test(lease.journal) ||
      lease.stage !== 'reserved'
    )
      fail();
    binding = read(dir, lease.journal);
    original = stamp(binding.predecessor);
    if (
      binding.schema !== 1 ||
      binding.protocol !== 'no-root-root-handoff-v1' ||
      binding.lease !== lease.id ||
      binding.operation !== lease.journal.slice(8, -5) ||
      original.lease === lease.id ||
      !/^[a-f0-9]{64}$/.test(binding.plan_sha256) ||
      !/^[a-f0-9]{64}$/.test(binding.source_sha256) ||
      typeof binding.effects_started !== 'boolean' ||
      (binding.revoked !== undefined && typeof binding.revoked !== 'boolean')
    )
      fail();
  } else fail();
  if (binding && binding.revoked === true && input.command !== 'release')
    fail();
  function promotionDescriptor() {
    try {
      fs.lstatSync('/var/lib/clean-your-tv-python');
    } catch (e) {
      if (e.code === 'ENOENT') return -1;
      throw e;
    }
    var parent = directory('/var/lib/clean-your-tv-python');
    var expected = fs.lstatSync(at(parent, '.install.lock'));
    var held = fs.fstatSync(4);
    owned(expected, false);
    owned(held, false);
    if (!same(expected, held)) fail();
    return 4;
  }
  function verify(mode) {
    var promotion = promotionDescriptor();
    var result = cp.spawnSync(
      '/usr/bin/node',
      [
        '-',
        mode || 'verify',
        original.operation,
        '-',
        '3',
        String(promotion),
        '5',
        '-',
        original.removal
      ],
      {
        input: input.cleanup,
        stdio: ['pipe', 'pipe', 'pipe', 3, promotion === 4 ? 4 : 'ignore', 5],
        timeout: 90000,
        maxBuffer: 2097152
      }
    );
    if (result.error || result.status !== 0) fail();
    var proof = JSON.parse(result.stdout.toString());
    if (
      proof.state !== 'verified-clean' ||
      proof.operation !== original.operation ||
      proof.removal !== original.removal ||
      !/^[a-f0-9]{32}$/.test(proof.lease)
    )
      fail();
    if (mode === 'finalize') {
      var current = read(dir, 'operation.json'),
        finished = read(dir, 'clean-removal-' + original.operation + '.json');
      if (
        current.id !== proof.lease ||
        current.owner !== 'clean-removal' ||
        current.journal !== 'product-' + original.operation + '.json' ||
        current.stage !== 'verified-clean' ||
        current.terminal !== false ||
        finished.final_fence !== proof.lease ||
        finished.stage !== 'verified-clean' ||
        finished.current !== true
      )
        fail();
      original.lease = proof.lease;
      lease = current;
    } else if (proof.lease !== original.lease) fail();
  }
  function closed() {
    if (!binding) fail();
    var privateDir = directory(
        '/tmp/.cytv-installer-root/operations/' + binding.operation
      ),
      value = read(privateDir, 'closed.json');
    if (
      value.protocol !== 'no-root-original-stream-v1' ||
      value.operation !== binding.operation ||
      value.plan_sha256 !== binding.plan_sha256 ||
      value.source_sha256 !== binding.source_sha256 ||
      value.result !== 'verified'
    )
      fail();
  }
  if (input.command === 'cleanup-target') {
    // A completed No-root successor may remove itself through the existing
    // shared Root cleaner. Classify only inert predecessor fences; never infer
    // this permission from directory names or an advisory host summary.
    closed();
    var predecessor = read(
      dir,
      'clean-removal-' + original.operation + '.json'
    );
    if (
      predecessor.final_fence !== original.lease ||
      predecessor.removal !== original.removal ||
      predecessor.stage !== 'verified-clean' ||
      predecessor.state !== 'complete' ||
      predecessor.current !== true ||
      !object(predecessor.result) ||
      predecessor.result.verified_clean !== true ||
      predecessor.result.private_cleanup_verified !== true
    )
      fail();
    var missing = function (path) {
      try {
        fs.lstatSync(path);
        fail();
      } catch (e) {
        if (e.code !== 'ENOENT') throw e;
      }
    };
    var rootApps = [
      'com.cleanyourtv.root.preview',
      'com.cleanyourtv.root.updater',
      'com.cleanyourtv.system.updater'
    ];
    rootApps.forEach(function (app) {
      ['applications/', 'services/', 'packages/'].forEach(function (kind) {
        missing(
          '/media/developer/apps/usr/palm/' +
            kind +
            app +
            (kind === 'services/' ? '.service' : '')
        );
      });
    });
    missing('/var/webos-profile/override/clean-your-tv-root.json');
    [
      '50-clean-your-tv-root',
      '51-clean-your-tv-root-updater',
      '52-clean-your-tv-system-updater'
    ].forEach(function (name) {
      missing('/var/lib/webosbrew/init.d/' + name);
    });
    ['root', 'root-updater', 'system-updater', 'python'].forEach(
      function (name, index) {
        var path = '/var/lib/clean-your-tv-' + name;
        try {
          fs.lstatSync(path);
        } catch (e) {
          if (e.code === 'ENOENT') return;
          throw e;
        }
        var leaf = directory(path),
          keep =
            index === 0
              ? ['deploy.json', 'provision.lock']
              : index === 3
                ? ['.install.lock']
                : ['bootstrap.json', 'daemon.lock', 'worker.lock'];
        if (
          fs.readdirSync(at(leaf)).some(function (name) {
            return keep.indexOf(name) === -1;
          })
        )
          fail();
      }
    );
    promotionDescriptor();
    process.stdout.write(
      JSON.stringify({
        lease: lease.id,
        operation: binding.operation,
        node: process.versions.node
      })
    );
    return;
  }
  if (input.command === 'probe') {
    if (binding) closed();
    else verify('finalize');
    process.stdout.write(JSON.stringify(original));
    return;
  }
  if (input.command === 'release') {
    if (!binding) {
      verify();
      process.stdout.write('{}');
      return;
    }
    // The ordinary No-root remover already proved restart and removed all its
    // private data. Verify total current absence while its successor is fenced.
    verify();
    binding.revoked = true;
    write(dir, lease.journal, binding);
    lease = {
      schema: 1,
      id: original.lease,
      owner: 'clean-removal',
      journal: 'product-' + original.operation + '.json',
      stage: 'verified-clean',
      terminal: false
    };
    write(dir, 'operation.json', lease);
    process.stdout.write('{}');
    return;
  }
  var plan = input.plan;
  if (
    !object(plan) ||
    plan.connection !== 'root-ssh' ||
    !/^[a-f0-9]{32}$/.test(plan.operation) ||
    canonical(stamp(plan.root_handoff)) !== canonical(original)
  )
    fail();
  var digest = sha(canonical(plan));
  if (input.command === 'continuation') {
    if (!binding || binding.operation !== plan.operation) {
      if (binding) closed();
      else verify();
      process.stdout.write(
        JSON.stringify({ operation: plan.operation, state: 'unclaimed' })
      );
      return;
    }
    if (
      binding.plan_sha256 !== digest ||
      binding.source_sha256 !== plan.source_sha256 ||
      typeof binding.effects_started !== 'boolean'
    )
      fail();
    var prepared = true;
    try {
      fs.lstatSync(
        '/tmp/.cytv-installer-root/operations/' +
          plan.operation +
          '/prepared.json'
      );
    } catch (e) {
      if (e.code !== 'ENOENT') throw e;
      prepared = false;
    }
    process.stdout.write(
      JSON.stringify({
        operation: plan.operation,
        state:
          !binding.effects_started && !prepared ? 'unprepared' : 'observing'
      })
    );
    return;
  }
  if (input.command === 'storage') {
    if (binding) closed();
    else verify();
    if (
      sha(input.source) !== plan.source_sha256 ||
      input.request.command !== 'storage-check'
    )
      fail();
    var created = [];
    ['/tmp/.cytv-installer-root', '/var/lib/clean-your-tv-installer'].forEach(
      function (path) {
        try {
          fs.lstatSync(path);
        } catch (e) {
          if (e.code !== 'ENOENT') throw e;
          created.push(path);
        }
      }
    );
    try {
      execute();
    } finally {
      // Only the empty leaves created by this read/write capability check. Never
      // remove an existing reservation, failed probe evidence or a replacement.
      created.forEach(function (path) {
        try {
          var fd = directory(path),
            s = fs.fstatSync(fd);
          if (
            fs.readdirSync(at(fd)).length === 0 &&
            same(s, fs.lstatSync(path))
          ) {
            fs.rmdirSync(path);
          }
        } catch (e) {
          if (e.code !== 'ENOENT') throw e;
        }
      });
    }
    return;
  }
  if (binding && binding.operation === plan.operation) {
    if (
      binding.plan_sha256 !== digest ||
      binding.source_sha256 !== plan.source_sha256
    )
      fail();
  } else {
    if (input.command !== 'claim') fail();
    if (binding) closed();
    else verify();
    binding = {
      schema: 1,
      protocol: 'no-root-root-handoff-v1',
      operation: plan.operation,
      lease: crypto.randomBytes(16).toString('hex'),
      predecessor: original,
      plan_sha256: digest,
      source_sha256: plan.source_sha256,
      effects_started: false
    };
    var name = 'no-root-' + plan.operation + '.json';
    // Reserve the binding before advertising its owner. A crash between writes
    // has no observer effects; retry must use the identical plan.
    try {
      var retained = read(dir, name);
      if (
        !/^[a-f0-9]{32}$/.test(retained.lease) ||
        retained.lease === original.lease
      )
        fail();
      binding.lease = retained.lease;
      if (canonical(retained) !== canonical(binding)) fail();
    } catch (e) {
      if (e.code !== 'ENOENT') throw e;
      write(dir, name, binding);
    }
    lease = {
      schema: 1,
      id: binding.lease,
      owner: 'no-root',
      journal: name,
      stage: 'reserved',
      terminal: false
    };
    write(dir, 'operation.json', lease);
  }
  if (input.command === 'claim') {
    process.stdout.write('{}');
    return;
  }
  if (
    input.command === 'observer' &&
    input.request.command === 'start' &&
    !binding.effects_started
  ) {
    binding.effects_started = true;
    write(dir, lease.journal, binding);
  }
  if (input.command === 'luna') {
    if (
      [
        'com.webos.service.eim/addDevice',
        'com.webos.applicationManager/launch'
      ].indexOf(input.uri) < 0
    )
      fail();
    var child = cp.spawn(
        '/usr/bin/luna-send',
        ['-n', '1', 'luna://' + input.uri, JSON.stringify(input.payload)],
        { stdio: ['pipe', 'pipe', 'pipe'] }
      ),
      text = '',
      done = false;
    var end = function (error, value) {
      if (done) return;
      done = true;
      clearTimeout(timer);
      child.stdin.end();
      child.kill();
      if (error) {
        process.stderr.write('root-successor-luna-unverified\n');
        process.exitCode = 1;
      } else process.stdout.write(JSON.stringify(value));
    };
    var timer = setTimeout(function () {
      end(true);
    }, 30000);
    child.stdin.on('error', function () {
      end(true);
    });
    child.stderr.on('data', function () {});
    child.stdout.on('data', function (data) {
      text += data.toString();
      if (text.length > 1048576) {
        end(true);
        return;
      }
      var value;
      try {
        value = JSON.parse(text);
      } catch (e) {
        return;
      }
      if (!object(value)) {
        end(true);
        return;
      }
      end(false, value);
    });
    child.on('error', function () {
      end(true);
    });
    child.on('close', function () {
      end(true);
    });
    return;
  }
  if (input.command !== 'observer' || sha(input.source) !== plan.source_sha256)
    fail();
  if (input.request.command === 'prepare' && plan.action === 'install') {
    if (
      canonical(input.request.plan) !== canonical(plan) ||
      input.request.root !== '/tmp/.cytv-installer-root' ||
      input.request.public_root !== '/var/lib/clean-your-tv-installer' ||
      input.request.sender !== '/usr/bin/luna-send' ||
      input.request.source !== input.source
    )
      fail();
    // The read/write capability probe restores clean absence. Preparation is
    // the successor's first durable use of this public staging parent, under
    // its exact lease and the original native locks. Keep the capsule unchanged.
    var stagingParent = directory('/var/lib'),
      stagingName = at(stagingParent, 'clean-your-tv-installer'),
      mask = process.umask(0);
    try {
      try {
        fs.mkdirSync(stagingName, 493);
      } catch (e) {
        if (e.code !== 'EEXIST') throw e;
      }
    } finally {
      process.umask(mask);
    }
    var staging = directory('/var/lib/clean-your-tv-installer');
    if ((fs.fstatSync(staging).mode & 4095) !== 493) fail();
    fs.fsyncSync(staging);
    fs.fsyncSync(stagingParent);
  }
  execute();
  function execute() {
    // Preserve the immutable observer source while retaining Root locks in its
    // detached worker. Passing explicit fd slots is necessary: spawn closes others.
    var wrapped = Object.create(cp);
    wrapped.spawn = function (command, args, options) {
      if (
        command === process.execPath &&
        Array.isArray(args) &&
        args[0] ===
          '/tmp/.cytv-installer-root/operations/' +
            plan.operation +
            '/observer.js'
      ) {
        var request = JSON.parse(args[1]);
        if (
          request.command !== 'worker' ||
          canonical(request.plan) !== canonical(plan)
        )
          fail();
        var child = {
          command: 'observer',
          plan: plan,
          source: input.source,
          request: request
        };
        var stdio = ['ignore', 'ignore', 'ignore', 3, 'ignore', 5];
        if (promotionDescriptor() === 4) stdio[4] = 4;
        var opts = { detached: true, stdio: stdio, cwd: options.cwd };
        child.wrapper = input.wrapper;
        return cp.spawn(
          process.execPath,
          ['-e', input.wrapper, JSON.stringify(child)],
          opts
        );
      }
      return cp.spawn(command, args, options);
    };
    var observerProcess = Object.create(process);
    observerProcess.argv = ['node', '-e', JSON.stringify(input.request)];
    vm.runInNewContext(input.source, {
      require: function (name) {
        return name === 'child_process' ? wrapped : require(name);
      },
      process: observerProcess,
      Buffer: Buffer,
      console: console,
      setTimeout: setTimeout,
      clearTimeout: clearTimeout,
      setImmediate: setImmediate
    });
  }
})();
'''


def call(remote, loaded, command, plan=None, source=None, request=None, data=None, uri=None, payload=None):
    cleanup,gate=loaded
    stage='/tmp/cytv-root-tail-'+uuid.uuid4().hex
    value=dict(command=command,wrapper=PROGRAM,stage=stage,gate_sha256=hashlib.sha256(gate).hexdigest())
    if command in ('probe','claim','release','storage','continuation','cleanup-target'):
        if data is not None:refuse()
        value['cleanup_stdin']=True
        data=cleanup.encode('utf8')
    if plan is not None:value['plan']=plan
    if source is not None:value.update(source=source,request=request)
    if uri is not None:value.update(uri=uri,payload=payload)
    remote.run('umask 077; mkdir '+stage)
    try:
        remote.upload(stage+'/gate',gate,mode=0o755)
        args=[stage+'/gate','root-clean-lock','/usr/bin/node','-e',PROGRAM,json.dumps(value,separators=(',',':'))]
        # Keep the same SSH stdin open while the detached original worker owns
        # the locks. In particular, a large legacy cleanup source must not race
        # an immediate exit 75 while SSH is still sending it.
        command=('unset NODE_OPTIONS NODE_PATH; cytv_guard_attempt=0; while :; do '+shlex.join(args)+
                 '; cytv_guard_status=$?; [ "$cytv_guard_status" -eq 75 ] || exit "$cytv_guard_status"; '
                 'cytv_guard_attempt=$((cytv_guard_attempt+1)); '
                 '[ "$cytv_guard_attempt" -lt 170 ] || exit 75; sleep 1; done')
        deadline=time.monotonic()+170
        while True:
            try:return remote.run(command,data=data,timeout=180)
            except TVCommandError as error:
                # Exit 75 belongs to the native nonblocking lock acquisition,
                # before Node or any observer/vendor effect was executed.
                if error.exit_status!=75 or time.monotonic()>=deadline:raise
                time.sleep(.25)
    finally:
        remote.run('if [ -d '+stage+' ]; then rm -f '+stage+'/gate; rmdir '+stage+'; fi')


def probe(installer):
    loaded=support(installer)
    value=validate(json.loads(call(installer.remote,loaded,'probe')))
    installer.remote._cytv_root_handoff_support=loaded
    return value


def cleanup_stamp(value):
    if (type(value) is not dict or set(value)!={'operation','lease','node'}
            or any(type(value.get(k)) is not str or not re.fullmatch('[a-f0-9]{32}',value[k]) for k in ('operation','lease'))
            or type(value.get('node')) is not str or not re.fullmatch(r'\d+\.\d+\.\d+',value['node'])):refuse()
    version=tuple(map(int,value['node'].split('.')))
    if version[0]<8 and version!=(0,12,2):refuse()
    return value


def cleanup_target(installer):
    return cleanup_stamp(json.loads(call(installer.remote,support(installer),'cleanup-target')))


def continuation(installer,plan):
    value=json.loads(call(installer.remote,installer.remote._cytv_root_handoff_support,'continuation',plan=plan))
    if (type(value) is not dict or value.get('operation')!=plan['operation']
            or value.get('state') not in ('unclaimed','unprepared','observing')):refuse()
    return value['state']


def release(installer):
    if installer.profile.get('connection')!='root-ssh':return
    from .root_runtime import FRESH_PROBE
    if installer.remote.run(FRESH_PROBE,timeout=10).strip()=='CYTV_FRESH_ROOT':return
    call(installer.remote,support(installer),'release')
