'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { Writable } = require('node:stream');
const EventEmitter = require('node:events');
const mediaPath = path.join(__dirname, '../screensaver/media.js');
assert.ok(
  fs.existsSync(mediaPath),
  'trusted screensaver media lease must exist'
);
const create = require(mediaPath).create;

function response(lease, method = 'GET', range, defer = false) {
  const req = new EventEmitter();
  req.method = method;
  req.headers = {};
  if (range !== undefined) req.headers.range = range;
  const chunks = [];
  const res = new Writable({
    highWaterMark: 1,
    write(chunk, encoding, done) {
      chunks.push(Buffer.from(chunk));
      setImmediate(done);
    }
  });
  res.writeHead = (status, headers) => {
    res.status = status;
    res.headers = headers;
  };
  const done = new Promise((resolve) => {
    res.on('finish', () =>
      resolve({
        status: res.status,
        headers: res.headers,
        bytes: Buffer.concat(chunks),
        destroyed: false
      })
    );
    res.on('close', () =>
      resolve({
        status: res.status,
        headers: res.headers,
        bytes: Buffer.concat(chunks),
        destroyed: !res.writableFinished
      })
    );
    res.on('error', () => {});
  });
  lease.serve(req, res);
  return defer ? { req, res, done } : done;
}

async function main() {
  const directory = fs.mkdtempSync(
    path.join(os.tmpdir(), 'screensaver-media-')
  );
  try {
    const file = path.join(directory, 'authorized.mp4');
    const original = Buffer.from('0123456789abcdef');
    fs.writeFileSync(file, original);
    const fd = fs.openSync(file, 'r');
    const lease = create({ fd, contentType: 'video/mp4' });
    assert.equal(lease.size, 16);
    assert.equal(lease.contentType, 'video/mp4');
    // Path replacement must never redirect an already-authorized descriptor.
    fs.renameSync(file, file + '.old');
    fs.writeFileSync(file, 'not authorized replacement');
    let result = await response(lease);
    assert.equal(result.status, 200);
    assert.deepEqual(result.bytes, original);
    assert.equal(result.headers['Content-Type'], 'video/mp4');
    assert.equal(result.headers['Content-Length'], 16);
    for (const [range, body, contentRange] of [
      ['bytes=2-5', '2345', 'bytes 2-5/16'],
      ['bytes=13-', 'def', 'bytes 13-15/16'],
      ['bytes=-3', 'def', 'bytes 13-15/16'],
      ['bytes=14-900', 'ef', 'bytes 14-15/16'],
      ['bytes=-100', '0123456789abcdef', 'bytes 0-15/16']
    ]) {
      result = await response(lease, 'GET', range);
      assert.equal(result.status, 206, range);
      assert.equal(result.bytes.toString(), body, range);
      assert.equal(result.headers['Content-Range'], contentRange, range);
    }
    for (const range of [
      'bytes=',
      'bytes=-0',
      'bytes=16-',
      'bytes=9-1',
      'bytes=1-2,4-5',
      'bytes=9007199254740992-',
      'bytes=0-9007199254740992',
      'items=0-1',
      'bytes=1.5-2',
      '',
      ['bytes=0-1']
    ]) {
      result = await response(lease, 'GET', range);
      assert.equal(result.status, 416, String(range));
      assert.equal(result.headers['Content-Range'], 'bytes */16');
      assert.equal(result.bytes.length, 0);
    }
    assert.equal((await response(lease, 'POST')).status, 405);
    result = await response(lease, 'HEAD', 'bytes=2-5');
    assert.equal(result.status, 206);
    assert.equal(result.headers['Content-Length'], 4);
    assert.equal(result.bytes.length, 0);
    lease.release();
    lease.release();
    assert.throws(() => fs.fstatSync(fd), /EBADF/);
    assert.equal((await response(lease)).status, 410);

    // Rejected construction does not steal ownership from the caller.
    const invalidFd = fs.openSync(file, 'r');
    assert.throws(() => create({ fd: invalidFd, contentType: 'text/html' }));
    assert.ok(fs.fstatSync(invalidFd).isFile());
    fs.closeSync(invalidFd);
    const directoryFd = fs.openSync(directory, 'r');
    assert.throws(() => create({ fd: directoryFd, contentType: 'video/mp4' }));
    fs.closeSync(directoryFd);
    assert.throws(() => create({ path: file, contentType: 'video/mp4' }));
    assert.throws(() =>
      create({
        size: 10,
        contentType: 'image/svg+xml',
        read() {},
        release() {}
      })
    );
    assert.throws(() =>
      create({
        size: 9007199254740992,
        contentType: 'image/png',
        read() {},
        release() {}
      })
    );

    let released = 0,
      reads = [];
    const data = Buffer.alloc(150000, 0x72);
    const provider = create({
      size: data.length,
      contentType: 'image/jpeg',
      read(offset, length, done) {
        reads.push({ offset, length });
        done(null, data.slice(offset, offset + length));
      },
      release() {
        released += 1;
      }
    });
    assert.equal((await response(provider, 'HEAD')).bytes.length, 0);
    assert.equal(reads.length, 0, 'HEAD cannot read source bytes');
    result = await response(provider);
    assert.deepEqual(result.bytes, data);
    assert.ok(reads.length >= 3);
    assert.ok(reads.every((r) => r.length > 0 && r.length <= 65536));
    assert.deepEqual(
      reads.map((r) => r.offset),
      [0, 65536, 131072]
    );
    provider.release();
    provider.release();
    assert.equal(released, 1);

    // A slow source cannot create unbounded parallel readers; release cancels all.
    const pending = [];
    released = 0;
    const slow = create({
      size: 8,
      contentType: 'video/mp4',
      read(offset, length, done) {
        pending.push(done);
      },
      release() {
        released += 1;
      }
    });
    const requests = [0, 1, 2, 3].map(() =>
      response(slow, 'GET', undefined, true)
    );
    await new Promise(setImmediate);
    assert.equal(pending.length, 4);
    assert.equal((await response(slow)).status, 503);
    slow.release();
    slow.release();
    pending.forEach((done) => done(null, Buffer.from('12345678')));
    for (const request of requests) {
      result = await request.done;
      assert.equal(result.destroyed, true);
      assert.equal(
        result.bytes.length,
        0,
        'late reads cannot deliver bytes after release'
      );
    }
    assert.equal(released, 1);

    // Broken or malicious providers must not stream beyond the approved extent.
    for (const read of [
      (offset, length, done) => done(null, Buffer.alloc(length + 1)),
      (offset, length, done) => done(null, Buffer.alloc(0)),
      (offset, length, done) => done(null, 'not bytes'),
      (offset, length, done) => done(new Error('unavailable')),
      () => {
        throw new Error('unavailable');
      }
    ]) {
      const broken = create({
        size: 8,
        contentType: 'image/png',
        read,
        release() {}
      });
      result = await response(broken);
      assert.equal(result.destroyed, true);
      assert.equal(result.bytes.length, 0);
      broken.release();
    }
    let readsAfterAbort = 0;
    const abort = create({
      size: 8,
      contentType: 'image/webp',
      read(offset, length, done) {
        readsAfterAbort += 1;
      },
      release() {}
    });
    const interrupted = response(abort, 'GET', undefined, true);
    interrupted.req.emit('aborted');
    await interrupted.done;
    await new Promise(setImmediate);
    assert.equal(readsAfterAbort, 0);
    abort.release();

    const empty = create({
      size: 0,
      contentType: 'image/png',
      read() {
        throw new Error('empty source read');
      },
      release() {}
    });
    assert.equal((await response(empty)).headers['Content-Length'], 0);
    assert.equal((await response(empty, 'GET', 'bytes=0-')).status, 416);
    empty.release();
    console.log(
      'PASS screensaver media: authorized descriptor, ranges, bounded streams, abort and idempotent cleanup'
    );
  } finally {
    fs.rmSync(directory, { recursive: true, force: true });
  }
}
main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
