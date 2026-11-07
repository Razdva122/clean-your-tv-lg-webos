/* Home uses logical 1920x1080 coordinates; trusted dialogs use the real viewport. */
(function (root) {
  'use strict';
  var scale = 1;
  function update() {
    var width = Number(root.innerWidth) || 1920,
      height = Number(root.innerHeight) || 1080;
    scale = Math.min(
      1,
      width > 0 ? width / 1920 : 1,
      height > 0 ? height / 1080 : 1
    );
    var scene = root.document.getElementById('homeSurface');
    if (scene) {
      scene.style.transform = 'scale(' + scale + ')';
      scene.style.webkitTransform = scene.style.transform;
    }
    return scale;
  }
  function rect(element) {
    var box = element.getBoundingClientRect(),
      scene = root.document.getElementById('homeSurface'),
      origin = scene ? scene.getBoundingClientRect() : { left: 0, top: 0 };
    return {
      left: (box.left - origin.left) / scale,
      top: (box.top - origin.top) / scale,
      right: (box.right - origin.left) / scale,
      bottom: (box.bottom - origin.top) / scale,
      width: box.width / scale,
      height: box.height / scale
    };
  }
  root.HomeViewport = { update: update, rect: rect };
  update();
  root.addEventListener('resize', update);
})(window);
