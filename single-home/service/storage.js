'use strict';

const crypto = require('crypto');
const OWNER = 'io.github.razdva122.cytvhomepilot.service';
const KIND = OWNER + '.store:1';
const DB = 'luna://com.palm.db/';
const KM = 'luna://com.webos.service.keymanager3/';
const KEY_NAME = 'CytvHomePilotGcm1';

function error(code) {
  const result = new Error(code);
  result.code = code;
  return result;
}

function fresh() {
  return {
    startup: 'off',
    generation: '',
    activityId: null,
    ownerVisit: null,
    receipt: null
  };
}

function bootState(state) {
  const id = /^[a-f0-9]{32}$/;
  function observation(value) {
    return (
      value &&
      typeof value.boot === 'string' &&
      /^[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}:[0-9]{1,12}$/i.test(
        value.boot
      ) &&
      Number.isSafeInteger(value.at) &&
      value.at >= 0
    );
  }
  if (
    !state ||
    !['off', 'pending', 'enabled', 'stopped'].includes(state.startup) ||
    !(
      state.generation === '' ||
      (typeof state.generation === 'string' && id.test(state.generation))
    ) ||
    !(
      state.activityId === null ||
      (Number.isSafeInteger(state.activityId) && state.activityId > 0)
    ) ||
    !(state.ownerVisit === null || observation(state.ownerVisit)) ||
    !(
      state.receipt === null ||
      (observation(state.receipt) &&
        id.test(state.receipt.generation) &&
        typeof state.receipt.early === 'boolean')
    )
  )
    throw error('storage-invalid-boot-state');
  const visit = state.ownerVisit;
  const receipt = state.receipt;
  return {
    startup: state.startup,
    generation: state.generation,
    activityId: state.activityId,
    ownerVisit: visit && { boot: visit.boot, at: visit.at },
    receipt: receipt && {
      boot: receipt.boot,
      at: receipt.at,
      generation: receipt.generation,
      early: receipt.early
    }
  };
}

function decode(value, maxBytes) {
  if (
    typeof value !== 'string' ||
    !value ||
    value.length > Math.ceil(maxBytes / 3) * 4
  )
    throw error('storage-invalid-envelope');
  const bytes = Buffer.from(value, 'base64');
  if (
    !bytes.length ||
    bytes.length > maxBytes ||
    bytes.toString('base64') !== value
  )
    throw error('storage-invalid-envelope');
  return bytes;
}

function validKey(key) {
  return (
    typeof key === 'string' &&
    key.length > 0 &&
    Buffer.byteLength(key, 'utf8') <= 1024
  );
}

module.exports = function createStorage(service) {
  let registered = false;
  let queue = Promise.resolve();
  function serialized(task) {
    const result = queue.then(task);
    queue = result.catch(() => {});
    return result;
  }

  function call(base, method, args) {
    const step = (base === DB ? 'storage-db-' : 'storage-keymanager-') + method;
    return new Promise((resolve, reject) => {
      let finished = false,
        timedOut = false;
      const timeout = setTimeout(() => {
        timedOut = true;
        finished = true;
        reject(error(step + '-timeout'));
      }, 5000);
      try {
        service.call(base + method, args, (message) => {
          const result = message && message.payload;
          if (finished) {
            // A late begin may have allocated an operation after our deadline.
            if (
              timedOut &&
              method === 'begin' &&
              result &&
              typeof result.handle === 'string' &&
              /^[0-9]{1,20}$/.test(result.handle)
            )
              call(KM, 'abort', { handle: result.handle }).catch(() => {});
            return;
          }
          clearTimeout(timeout);
          finished = true;
          if (result && result.returnValue === true) resolve(result);
          else {
            const number = result && result.errorCode;
            const reason = error(
              step + (Number.isSafeInteger(number) ? ':' + number : '-failed')
            );
            reason.platformCode = number;
            reject(reason);
          }
        });
      } catch (_) {
        clearTimeout(timeout);
        finished = true;
        reject(error(step + '-unavailable'));
      }
    });
  }

  async function find() {
    const reply = await call(DB, 'find', { query: { from: KIND, limit: 2 } });
    if (!Array.isArray(reply.results) || reply.results.length > 1 || reply.next)
      throw error('storage-invalid-db-results');
    if (!reply.results.length) return null;
    const row = reply.results[0];
    if (
      !row ||
      row._kind !== KIND ||
      typeof row._id !== 'string' ||
      !row._id ||
      !Number.isSafeInteger(row._rev) ||
      row._rev < 1 ||
      row.schema !== 1 ||
      typeof row.canary !== 'string' ||
      !/^[a-f0-9]{64}$/.test(row.canary) ||
      !(row.proof === null || (row.proof && typeof row.proof === 'object')) ||
      !(
        row.secret === null ||
        (row.secret && typeof row.secret === 'object' && row.proof)
      )
    )
      throw error('storage-invalid-record');
    bootState(row.boot);
    return row;
  }

  function sameEnvelope(a, b) {
    return a === b || (!!a && !!b && a.iv === b.iv && a.data === b.data);
  }

  function sameRecord(actual, expected) {
    return (
      actual &&
      (!expected._id || actual._id === expected._id) &&
      actual.canary === expected.canary &&
      sameEnvelope(actual.proof, expected.proof) &&
      sameEnvelope(actual.secret, expected.secret) &&
      JSON.stringify(bootState(actual.boot)) ===
        JSON.stringify(bootState(expected.boot))
    );
  }

  async function put(row) {
    const reply = await call(DB, 'put', { objects: [row] });
    const saved = reply.results && reply.results[0];
    if (
      !saved ||
      reply.results.length !== 1 ||
      typeof saved.id !== 'string' ||
      !Number.isSafeInteger(saved.rev) ||
      saved.rev < 1 ||
      (row._id && saved.id !== row._id)
    )
      throw error('storage-invalid-db-receipt');
    const confirmed = await find();
    if (
      !confirmed ||
      confirmed._id !== saved.id ||
      confirmed._rev !== saved.rev ||
      !sameRecord(confirmed, row)
    )
      throw error('storage-write-not-confirmed');
    return confirmed;
  }

  // DB8 revision checks serialize competing writes. After a lost acknowledgement,
  // reconcile the full authenticated candidate, never replay a replacement blindly.
  async function commitCredential(previous, candidate) {
    if (sameRecord(previous, candidate)) return;
    try {
      await put(candidate);
    } catch (cause) {
      let observed;
      try {
        observed = await find();
      } catch (_) {}
      if (sameRecord(observed, candidate) && observed._rev > previous._rev)
        return;
      // A timed-out request can still reach DB8 after this read.
      if (
        sameRecord(observed, previous) &&
        observed._rev === previous._rev &&
        cause.code !== 'storage-db-put-timeout' &&
        cause.code !== 'storage-db-put-unavailable'
      ) {
        throw cause;
      }
      throw error('storage-credential-write-indeterminate');
    }
  }

  async function load() {
    if (!registered) {
      // DB8 checks the actual LS2 caller against owner. No permissions are granted.
      await call(DB, 'putKind', { id: KIND, owner: OWNER, private: true });
      registered = true;
    }
    const existing = await find();
    if (existing) return existing;
    return put({
      _kind: KIND,
      schema: 1,
      canary: crypto.randomBytes(32).toString('hex'),
      proof: null,
      secret: null,
      boot: fresh()
    });
  }

  async function crypt(purpose, role, input) {
    const encrypt = purpose === 'encrypt';
    const params = {
      type: 'AES',
      mode: ['GCM'],
      purpose: [purpose],
      padding: ['None'],
      mac_length: '128'
    };
    let data;
    if (encrypt) data = Buffer.from(input, 'utf8');
    else {
      if (!input || decode(input.iv, 12).length !== 12)
        throw error('storage-invalid-iv');
      params.iv = input.iv;
      data = decode(input.data, 1040);
      if (data.length <= 16) throw error('storage-invalid-envelope');
    }
    const operation = await call(KM, 'begin', { name: KEY_NAME, params });
    const handle = operation.handle;
    if (typeof handle !== 'string' || !/^[0-9]{1,20}$/.test(handle))
      throw error('storage-invalid-handle');
    try {
      if (encrypt && decode(operation.iv, 12).length !== 12)
        throw error('storage-invalid-iv');
      const reply = await call(KM, 'finish', {
        handle,
        data: data.toString('base64'),
        aad: Buffer.from(KIND + '/' + role, 'utf8').toString('base64')
      });
      const output = decode(reply.output, 1040);
      if (output.length !== data.length + (encrypt ? 16 : -16))
        throw error('storage-invalid-gcm-output');
      return encrypt
        ? { iv: operation.iv, data: reply.output }
        : output.toString('utf8');
    } catch (reason) {
      try {
        await call(KM, 'abort', { handle });
      } catch (_) {}
      throw reason;
    }
  }

  async function verified(row) {
    if (!row.proof) {
      const params = {
        type: 'AES',
        size: 256,
        mode: ['GCM'],
        purpose: ['encrypt', 'decrypt'],
        // The operation sets its tag length at begin; some TVs reject it here.
        padding: ['None']
      };
      try {
        await call(KM, 'generateKey', { name: KEY_NAME, params });
      } catch (reason) {
        if (reason.platformCode !== -10002) throw reason;
      }
      row.proof = await crypt('encrypt', 'canary', row.canary);
      row = await put(row);
    }
    if ((await crypt('decrypt', 'canary', row.proof)) !== row.canary)
      throw error('storage-canary-mismatch');
    return row;
  }

  return {
    probe: () =>
      serialized(async () => {
        await load();
        return true;
      }),
    evidence: () =>
      serialized(async () => ({
        canarySha256: crypto
          .createHash('sha256')
          .update((await load()).canary, 'utf8')
          .digest('hex')
      })),
    credentialsReady: () =>
      serialized(async () => {
        await verified(await load());
        return true;
      }),
    readBoot: () =>
      serialized(async () => {
        const row = await load();
        return Object.assign(bootState(row.boot), { paired: !!row.secret });
      }),
    writeBoot: (state) =>
      serialized(async () => {
        const row = await load();
        row.boot = bootState(state);
        await put(row);
      }),
    read: () =>
      serialized(async () => {
        const row = await load();
        let key = null;
        if (row.secret) {
          await verified(row);
          key = await crypt('decrypt', 'credential', row.secret);
          if (!validKey(key)) throw error('storage-invalid-credential');
        }
        return Object.assign(bootState(row.boot), { key });
      }),
    write: (state) =>
      serialized(async () => {
        let row = await load();
        const boot = bootState(state);
        let secret = null;
        if (state.key !== null) {
          if (!validKey(state.key)) throw error('storage-invalid-credential');
          row = await verified(row);
          secret = await crypt('encrypt', 'credential', state.key);
          if ((await crypt('decrypt', 'credential', secret)) !== state.key)
            throw error('storage-credential-not-confirmed');
        }
        await commitCredential(row, Object.assign({}, row, { boot, secret }));
      })
  };
};
