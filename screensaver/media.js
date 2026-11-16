'use strict';

var fs = require('fs');
var types = ['image/jpeg', 'image/png', 'image/webp', 'video/mp4'];
var maxInteger = 9007199254740991;
var chunkBytes = 65536;
var maxReaders = 4;

function integer(value) {
  return (
    typeof value === 'number' &&
    isFinite(value) &&
    value >= 0 &&
    value <= maxInteger &&
    Math.floor(value) === value
  );
}

function rangeFor(header, size) {
  if (header === undefined) return { start: 0, end: size - 1, status: 200 };
  if (typeof header !== 'string' || header.length > 128 || !size) return null;
  var match = /^bytes=(\d*)-(\d*)$/.exec(header);
  if (!match || (!match[1] && !match[2])) return null;
  var first = match[1] ? Number(match[1]) : null;
  var last = match[2] ? Number(match[2]) : null;
  if ((first !== null && !integer(first)) || (last !== null && !integer(last)))
    return null;
  if (first === null) {
    if (!last) return null;
    first = Math.max(0, size - last);
    last = size - 1;
  } else {
    if (last === null) last = size - 1;
    last = Math.min(last, size - 1);
  }
  if (first > last || first >= size) return null;
  return { start: first, end: last, status: 206 };
}

// This is a trusted owner API, never a request payload parser. The caller must
// authorize a cache asset before transferring its open regular-file descriptor.
// A provider instead supplies {size, contentType, read, release}; read receives
// (offset, length, callback), callback(err, Buffer). Bytes must belong to the
// already-authorized immutable asset. No path or URL is opened by this module.
// Authentication, session checks and routing belong to the owning transport.
exports.create = function (source) {
  if (!source || types.indexOf(source.contentType) < 0)
    throw new Error('Unsupported media type');
  var type = source.contentType;
  var size;
  var read;
  var releaseSource;
  if (source.fd !== undefined) {
    if (!integer(source.fd)) throw new Error('Invalid media descriptor');
    var fd = source.fd;
    var stat = fs.fstatSync(fd);
    if (!stat.isFile() || !integer(stat.size))
      throw new Error('Media must be a regular file');
    size = stat.size;
    read = function (offset, length, done) {
      // Only the initialized prefix returned by fs.read is exposed.
      var buffer = Buffer.alloc ? Buffer.alloc(length) : new Buffer(length);
      fs.read(fd, buffer, 0, length, offset, function (error, count) {
        done(error, error ? null : buffer.slice(0, count));
      });
    };
    releaseSource = function () {
      fs.closeSync(fd);
    };
  } else {
    if (
      !integer(source.size) ||
      typeof source.read !== 'function' ||
      typeof source.release !== 'function'
    ) {
      throw new Error('Invalid authorized media provider');
    }
    size = source.size;
    var providerRead = source.read;
    var providerRelease = source.release;
    read = function (offset, length, done) {
      providerRead.call(source, offset, length, done);
    };
    releaseSource = function () {
      providerRelease.call(source);
    };
  }
  var released = false;
  var readers = [];

  function serve(req, res) {
    function end(status, extra) {
      var headers = { 'Content-Length': 0, 'Cache-Control': 'no-store' };
      if (extra)
        Object.keys(extra).forEach(function (key) {
          headers[key] = extra[key];
        });
      res.writeHead(status, headers);
      res.end();
    }
    if (released) return end(410);
    if (req.method !== 'GET' && req.method !== 'HEAD')
      return end(405, { Allow: 'GET, HEAD' });
    var range = rangeFor((req.headers || {}).range, size);
    if (!range) return end(416, { 'Content-Range': 'bytes */' + size });
    if (req.method === 'GET' && readers.length >= maxReaders) return end(503);
    var headers = {
      'Content-Type': type,
      'Content-Length': range.end - range.start + 1,
      'Accept-Ranges': 'bytes',
      'Cache-Control': 'no-store',
      'X-Content-Type-Options': 'nosniff'
    };
    if (range.status === 206)
      headers['Content-Range'] =
        'bytes ' + range.start + '-' + range.end + '/' + size;
    res.writeHead(range.status, headers);
    if (req.method === 'HEAD' || !size) return res.end();

    var offset = range.start;
    var closed = false;
    var timer = setTimeout(abort, 15000);
    var reader = { abort: abort };
    readers.push(reader);
    function cleanup() {
      if (closed) return;
      closed = true;
      clearTimeout(timer);
      var index = readers.indexOf(reader);
      if (index >= 0) readers.splice(index, 1);
      req.removeListener('aborted', abort);
      req.removeListener('error', abort);
      res.removeListener('drain', next);
      res.removeListener('finish', cleanup);
      res.removeListener('close', cleanup);
      res.removeListener('error', abort);
    }
    function abort() {
      if (closed) return;
      cleanup();
      res.destroy();
    }
    function next() {
      if (closed || released) return;
      var count = Math.min(chunkBytes, range.end - offset + 1);
      var called = false;
      try {
        read(offset, count, function (error, bytes) {
          if (called) return;
          called = true;
          if (closed || released) return;
          if (
            error ||
            !Buffer.isBuffer(bytes) ||
            !bytes.length ||
            bytes.length > count
          )
            return abort();
          offset += bytes.length;
          clearTimeout(timer);
          timer = setTimeout(abort, 15000);
          try {
            var writable = res.write(bytes);
            if (offset > range.end) res.end();
            else if (writable) process.nextTick(next);
            else res.once('drain', next);
          } catch (ignore) {
            abort();
          }
        });
      } catch (ignore) {
        abort();
      }
    }
    req.once('aborted', abort);
    req.once('error', abort);
    res.once('finish', cleanup);
    res.once('close', cleanup);
    res.once('error', abort);
    process.nextTick(next);
  }

  return {
    contentType: type,
    size: size,
    serve: serve,
    release: function () {
      if (released) return;
      released = true;
      readers.slice().forEach(function (reader) {
        reader.abort();
      });
      try {
        releaseSource();
      } catch (ignore) {}
    }
  };
};
