/* Small, inert Markdown subset shared by both TV update dialogs. */
(function () {
  'use strict';
  function inline(parent, text) {
    var pattern =
      /\[([^\]]+)\]\([^)]*\)|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*]+)\*|_([^_]+)_|`([^`]+)`/g;
    var match,
      offset = 0;
    while ((match = pattern.exec(text))) {
      if (match.index > offset)
        parent.appendChild(
          document.createTextNode(text.slice(offset, match.index))
        );
      var label =
        match[1] || match[2] || match[3] || match[4] || match[5] || match[6];
      if (match[1]) parent.appendChild(document.createTextNode(label));
      else {
        var span = document.createElement(
          match[2] || match[3] ? 'strong' : match[6] ? 'code' : 'em'
        );
        span.textContent = label;
        parent.appendChild(span);
      }
      offset = pattern.lastIndex;
    }
    if (offset < text.length)
      parent.appendChild(document.createTextNode(text.slice(offset)));
  }
  function render(container, source) {
    source = String(source || '').replace(/\r\n?/g, '\n');
    if (container._releaseNotesSource === source) return;
    container._releaseNotesSource = source;
    container.textContent = '';
    container.scrollTop = 0;
    var list = null,
      paragraph = null;
    source.split('\n').forEach(function (line) {
      var heading = /^(#{1,6})\s+(.+?)\s*#*\s*$/.exec(line);
      var item = /^\s*(?:[-*+]\s+|\d+[.)]\s+)(.*)$/.exec(line);
      if (!line.trim()) {
        list = null;
        paragraph = null;
        return;
      }
      if (heading) {
        list = null;
        paragraph = null;
        var h = document.createElement(heading[1].length <= 2 ? 'h2' : 'h3');
        inline(h, heading[2]);
        container.appendChild(h);
      } else if (item) {
        paragraph = null;
        var tag = /^\s*\d/.test(line) ? 'ol' : 'ul';
        if (!list || list._listTag !== tag) {
          list = document.createElement(tag);
          list._listTag = tag;
          container.appendChild(list);
        }
        var li = document.createElement('li');
        inline(li, item[1]);
        list.appendChild(li);
      } else {
        list = null;
        if (!paragraph) {
          paragraph = document.createElement('p');
          container.appendChild(paragraph);
        } else paragraph.appendChild(document.createTextNode(' '));
        inline(paragraph, line);
      }
    });
  }
  function scroll(container, direction) {
    var limit = Math.max(0, container.scrollHeight - container.clientHeight);
    container.scrollTop = Math.max(
      0,
      Math.min(
        limit,
        container.scrollTop +
          direction * Math.max(80, Math.floor(container.clientHeight * 0.75))
      )
    );
  }
  window.HomeReleaseNotes = { render: render, scroll: scroll };
})();
