"""Build-only deterministic Chinese fonts; never modify retained source assets."""
import ast
import base64
from functools import lru_cache
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = {'SC': 'zh-Hans', 'TC': 'zh-Hant'}
VERSION = '4.60.1'
REVISION = 'e7db6ca603fd4862010383ff17ffd6cc4ffac1c0'
SOURCES = {
    'SC': {'sha256': 'a3041811a78c361b1de50f953c805e0244951c21c5bd412f7232ef0d899af0da', 'size': 17772300},
    'TC': {'sha256': '864727d210d54f2537bbe23b3a839436c3992af72de9322af5270897246bd44f', 'size': 11941968},
}
# Runtime roots only: no tests, documentation, research, vendored code or npm tree.
JS_ROOTS = ('launcher', 'root-edition/ui', 'updater-app', 'root-edition/updater/app',
            'homebrew/app', 'android/app/src/main/assets/ui')
COLLECT = r"""
const fs=require('fs'),acorn=require('acorn'),postcss=require('postcss'),html=require('parse5');
const out={'zh-Hans':[],'zh-Hant':[],shared:[]},chinese=['zh-Hans','zh-Hant'],locales=new Set(['en','cs','de','es','pt-BR','fr','it','ko','hi','pl','ru',...chinese]);
function known(value){return typeof value==='string'&&(['zh','pt'].includes(value.replace(/_/g,'-').split('-')[0].toLowerCase())||locales.has(value.replace(/_/g,'-').split('-')[0].toLowerCase()));}
function language(value){const parts=String(value).replace(/_/g,'-').toLowerCase().split('-');return parts[0]==='zh'?(parts.includes('hant')||parts.some(p=>['tw','hk','mo'].includes(p))?'zh-Hant':'zh-Hans'):'foreign';}
function emit(value,scope){if(scope!=='foreign')out[scope||'shared'].push(value);}
function visit(node,scope){if(!node||typeof node!=='object')return;
 if(node.type==='ObjectExpression'){
  const code=node.properties.find(p=>p.type==='Property'&&['code','lang','language'].includes(p.key.value||p.key.name)&&p.value.type==='Literal'&&known(p.value.value));
  if(code){scope=language(code.value.value);if(scope==='foreign')return;}}
 if(node.type==='Property'&&known(node.key.value||node.key.name)){
  const scope=language(node.key.value||node.key.name);if(scope!=='foreign')visit(node.value,scope);return;}
 if(node.type==='Literal'&&typeof node.value==='string')emit(node.value,scope);
 if(node.type==='TemplateElement'&&typeof node.value.cooked==='string')emit(node.value.cooked,scope);
 for(const value of Object.values(node)){if(Array.isArray(value))value.forEach(n=>visit(n,scope));else if(value&&typeof value==='object')visit(value,scope);}}
function js(source,scope){visit(acorn.parse(source,{ecmaVersion:'latest',sourceType:'script'}),scope);}
function data(value,scope){if(typeof value==='string'){emit(value,scope);return;}
 if(Array.isArray(value)){value.forEach(v=>data(v,scope));return;}
 if(!value||typeof value!=='object')return;
 const code=value.code||value.lang||value.language;if(known(code)){scope=language(code);if(scope==='foreign')return;}
 for(const [key,item] of Object.entries(value)){
  if(known(key)){const scope=language(key);if(scope!=='foreign')data(item,scope);}else{emit(key,scope);data(item,scope);}}}
function css(source,scope){postcss.parse(source).walkDecls(decl=>{
 const scopes=(decl.parent.selector||'').split(',').map(selector=>{
  if(/:(?:not|is|where|has)\(/.test(selector))return undefined;
  const tags=[...selector.matchAll(/:lang\(\s*["']?([^\s)"']+)["']?\s*\)|\[lang\s*(?:\|)?=\s*["']?([^\s\]"']+)["']?\s*\]/g)];
  const codes=[...new Set(tags.map(match=>language(match[1]||match[2])))];return codes.length===1?codes[0]:undefined;
 });
 const selected=scopes.every(code=>code===scopes[0])?scopes[0]:scope;
 emit(decl.value.replace(/\\([0-9a-fA-F]{1,6})(?:\r\n|[ \t\r\n\f])?/g,(_,code)=>{const value=parseInt(code,16);return String.fromCodePoint(!value||value>0x10ffff||value>=0xd800&&value<=0xdfff?0xfffd:value);}),selected);
 });}
function markup(node,scope){
 const attrs=Object.fromEntries((node.attrs||[]).map(a=>[a.name,a.value]));if(attrs.lang)scope=language(attrs.lang);
 for(const [key,value] of Object.entries(attrs)){if(key==='style')css('x{'+value+'}',scope);else if(key.startsWith('on'))js(value,scope);else emit(value,scope);}
 if(node.tagName==='script'){
  const source=(node.childNodes||[]).map(n=>n.value||'').join('');
  const own=attrs.lang?language(attrs.lang):undefined;
  if((attrs.type||'').includes('json'))data(JSON.parse(source),own);else if((attrs.type||'').includes('html'))markup(html.parseFragment(source),own);else js(source,own);return;}
 if(node.tagName==='style'){css((node.childNodes||[]).map(n=>n.value||'').join(''),attrs.lang?language(attrs.lang):undefined);return;}
 if(node.nodeName==='#text')emit(node.value,scope);
 for(const child of node.childNodes||[])markup(child,scope);
 if(node.content)markup(node.content,scope);
}
for(const [kind,source] of JSON.parse(fs.readFileSync(0,'utf8'))){
 if(kind==='.js')js(source);else if(kind==='.json')data(JSON.parse(source));else if(kind==='.css')css(source);else markup(html.parse(source));}
process.stdout.write(JSON.stringify(out));
"""


def default_cache(root=ROOT):
    return Path(os.environ.get('CYTV_FONT_CACHE', str(Path(root)/'build/chinese-font-cache')))


def required_characters(root=ROOT, files=None):
    """Read decoded per-locale literals from every first-party runtime catalog."""
    root = Path(root)
    kinds = ('.js', '.html', '.css', '.json')
    sources = [(p.suffix, p.read_text(encoding='utf-8')) for directory in JS_ROOTS
               for p in sorted((root/directory).glob('*')) if p.suffix in kinds and p.is_file()]
    sources.extend((Path(name).suffix, raw.decode('utf-8')) for name, raw in sorted((files or {}).items())
                   if Path(name).suffix in kinds)
    python = root/'cytv/translations.py'
    python_text = python.read_text(encoding='utf-8') if python.is_file() else ''
    return {script: set(codes) for script, codes in _characters(tuple(sources), python_text).items()}


@lru_cache(maxsize=8)
def _characters(sources, python_text):
    result = subprocess.run(['node', '-e', COLLECT], input=json.dumps(sources),
                            text=True, encoding='utf-8', capture_output=True, cwd=ROOT,
                            timeout=30, check=True)
    text = json.loads(result.stdout)
    # Read only literal Python catalog data; do not execute runtime source code.
    constants = {}
    for node in ast.parse(python_text).body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ('LANGS', 'ROWS'):
                    constants[target.id] = ast.literal_eval(node.value)
    for row in constants.get('ROWS', '').splitlines():
        if not row.strip():
            continue
        values = row.split('|')
        for locale in SCRIPTS.values():
            text[locale].append(values[1+constants['LANGS'].index(locale)])
    shared = '年月日星期周週一二三四五六天上午下午'
    labels = {'SC': '简体中文', 'TC': '繁體中文'}
    # Other scripts retain their own faces; include CJK punctuation and extensions.
    def chinese(code):
        return (0x2000 <= code <= 0x9fff or 0xf900 <= code <= 0xfaff
                or 0xff00 <= code <= 0xffef or 0x20000 <= code <= 0x323af)
    generic = {ord(c) for c in ''.join(text['shared']) if chinese(ord(c))}
    required = {script: {ord(c) for c in ''.join(text[locale])+shared+labels[script] if chinese(ord(c))} | generic
                for script, locale in SCRIPTS.items()}
    required['_shared'] = generic
    return required



def tables(raw):
    count = struct.unpack_from('>H', raw, 4)[0]
    result = {}
    for i in range(count):
        tag, _, offset, length = struct.unpack_from('>4sIII', raw, 12+16*i)
        if offset+length > len(raw):
            raise ValueError('Truncated font')
        result[tag] = raw[offset:offset+length]
    return result


def coverage(raw):
    table = tables(raw)[b'cmap']
    result = set()
    for i in range(struct.unpack_from('>H', table, 2)[0]):
        _, _, offset = struct.unpack_from('>HHI', table, 4+8*i)
        fmt = struct.unpack_from('>H', table, offset)[0]
        if fmt == 4:
            count = struct.unpack_from('>H', table, offset+6)[0]//2
            ends = struct.unpack_from('>'+str(count)+'H', table, offset+14)
            starts = struct.unpack_from('>'+str(count)+'H', table, offset+16+2*count)
            deltas = struct.unpack_from('>'+str(count)+'h', table, offset+16+4*count)
            ranges = offset+16+6*count
            for segment, (start, end, delta) in enumerate(zip(starts, ends, deltas)):
                distance = struct.unpack_from('>H', table, ranges+2*segment)[0]
                for code in range(start, end+1):
                    glyph = struct.unpack_from('>H', table, ranges+2*segment+distance+2*(code-start))[0] if distance else code
                    if glyph and (glyph+delta)&0xffff:
                        result.add(code)
        elif fmt == 12:
            for j in range(struct.unpack_from('>I', table, offset+12)[0]):
                start, end, glyph = struct.unpack_from('>III', table, offset+16+12*j)
                result.update(range(start+(glyph == 0), end+1))
    return result


def static_regular(raw):
    font = tables(raw)
    return b'fvar' not in font and struct.unpack_from('>H', font[b'OS/2'], 4)[0] == 400


def checked_path(path):
    if any(parent.is_symlink() for parent in (path, *path.parents)):
        raise ValueError('Indirect Chinese font cache')
    return path


def atomic(path, raw):
    checked_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.font-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def source_font(script, cache):
    spec = SOURCES[script]
    path = checked_path(Path(cache).resolve()/'sources'/spec['sha256'])
    if path.exists():
        if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size != spec['size']:
            raise ValueError('Chinese font source cache integrity mismatch')
        raw = path.read_bytes()
    else:
        url = (f'https://raw.githubusercontent.com/google/fonts/{REVISION}/ofl/'
               f'notosans{script.lower()}/NotoSans{script}%5Bwght%5D.ttf')
        with urllib.request.urlopen(url, timeout=90) as reply:
            if reply.geturl() != url:
                raise ValueError('Unexpected Chinese font source redirect')
            raw = reply.read(spec['size']+1)
    if len(raw) != spec['size'] or hashlib.sha256(raw).hexdigest() != spec['sha256']:
        raise ValueError('Chinese font source integrity mismatch')
    if not path.exists():
        atomic(path, raw)
    return raw


@lru_cache(maxsize=8)
def _source_coverage(script, cache):
    return coverage(source_font(script, cache))


def prepare_fonts(root=ROOT, cache=None, files=None):
    root = Path(root)
    cache = (default_cache(root) if cache is None else Path(cache)).resolve()
    required = required_characters(root, files=files)
    retained = {script: (root/f'launcher/fonts/NotoSans{script}.ttf').read_bytes() for script in SCRIPTS}
    available = {script: coverage(raw) for script, raw in retained.items()}
    if not all(static_regular(retained[script]) and required[script] <= available[script] for script in SCRIPTS):
        # Either face may supply a quoted brand/theme name; keep each face's own
        # regional outlines wherever its pinned original supports the character.
        needed = set.union(*required.values())
        supported = {script: _source_coverage(script, str(cache)) for script in SCRIPTS}
        missing = needed-set.union(*supported.values())
        if missing:
            raise ValueError('Chinese source font lacks runtime characters: '+','.join(f'U+{c:04X}' for c in sorted(missing)))
        required = {script: needed & supported[script] for script in SCRIPTS}
    output = {}
    for script in SCRIPTS:
        name = f'fonts/NotoSans{script}.ttf'
        if static_regular(retained[script]) and required[script] <= available[script]:
            output[name] = retained[script]
            continue
        inputs = {'source': SOURCES[script]['sha256'], 'fonttools': VERSION,
                  'weight': 400, 'characters': sorted(required[script]), 'schema': 1}
        key = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()
        path = checked_path(cache/'subsets'/(key+'.json'))
        if path.exists():
            try:
                if not stat.S_ISREG(path.stat().st_mode) or path.stat().st_size > 4*1024*1024:
                    raise ValueError('Oversized font cache')
                record = json.loads(path.read_bytes())
                raw = base64.b64decode(record['data'], validate=True)
                if record['inputs'] != inputs or hashlib.sha256(raw).hexdigest() != record['sha256']:
                    raise ValueError('Invalid font cache')
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError('Chinese font cache integrity mismatch') from error
        else:
            try:
                import fontTools
                from fontTools import subset
                from fontTools.ttLib import TTFont
                from fontTools.varLib.instancer import instantiateVariableFont
                if fontTools.__version__ != VERSION:
                    raise ImportError('Wrong fonttools version')
            except ImportError as error:
                raise RuntimeError('Chinese font preparation requires python -m pip install -r scripts/build-requirements.txt') from error
            font = TTFont(io.BytesIO(source_font(script, cache)), recalcTimestamp=False)
            missing = required[script]-set(font.getBestCmap())
            if missing:
                raise ValueError('Chinese source font lacks runtime characters: '+','.join(f'U+{c:04X}' for c in sorted(missing)))
            font = instantiateVariableFont(font, {'wght': 400}, inplace=True, updateFontNames=True)
            options = subset.Options()
            options.recalc_timestamp = False
            sub = subset.Subsetter(options=options)
            sub.populate(unicodes=required[script])
            sub.subset(font)
            stream = io.BytesIO()
            font.save(stream)
            raw = stream.getvalue()
            record = {'inputs': inputs, 'sha256': hashlib.sha256(raw).hexdigest(),
                      'data': base64.b64encode(raw).decode('ascii')}
            atomic(path, json.dumps(record, sort_keys=True).encode())
        if len(raw) > 1024*1024 or not static_regular(raw) or not required[script] <= coverage(raw):
            raise ValueError('Chinese font cache has invalid static glyph coverage or size')
        output[name] = raw
    return output


def with_fonts(files):
    """Replace only fonts already admitted by a caller's explicit asset inventory."""
    if any(f'fonts/NotoSans{s}.ttf' in files for s in SCRIPTS):
        prepared = prepare_fonts(files=files)
        return {name: prepared.get(name, raw) for name, raw in files.items()}
    return files
