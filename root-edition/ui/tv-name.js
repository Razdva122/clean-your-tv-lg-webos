(function (root, factory) {
  'use strict';
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.HomeName = factory(root);
})(this, function (root) {
  'use strict';
  function normalize(value) {
    if (typeof value !== 'string') throw Error('Invalid Home screen name');
    value = value.replace(/^\s+|\s+$/g, '') || 'Home';
    if (value.normalize) value = value.normalize('NFC');
    var pairs = /[\ud800-\udbff][\udc00-\udfff]/g;
    if (
      value.replace(pairs, 'x').length > 48 ||
      /[\u0000-\u001f\u007f-\u009f\u00ad\u061c\u200b-\u200f\u2028-\u202e\u2060-\u206f\ufeff]/.test(
        value
      ) ||
      /[\ud800-\udfff]/.test(value.replace(pairs, ''))
    )
      throw Error('Invalid Home screen name');
    return value;
  }
  function refresh() {
    try {
      var saved = root.localStorage.getItem('tvhome.name');
      if (saved !== null) root.document.title = normalize(saved);
    } catch (_) {}
  }
  return { normalize: normalize, refresh: refresh };
});
