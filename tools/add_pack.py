#!/usr/bin/env python3
"""驗證 UTF-8 JSON 題庫，產生 classic JS，並更新 SHIFT 題庫目錄。

只使用 Python 3.9 以上的標準函式庫；不執行題庫或目錄中的 JavaScript。
"""

import argparse
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile


LIMIT_BYTES = 20 * 1024 * 1024
LIMIT_QUESTIONS = 5000
BUILTIN_IDS = {'test-01', 'test-02'}
FORBIDDEN_KEYS = {'__proto__', 'prototype', 'constructor'}
ID_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9._:-]{0,95}\Z')
PACK_ID_PATTERN = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}\Z')
TOPICS = {'technology', 'manufacturing', 'business', 'daily'}
DIFFICULTIES = {'foundation', 'intermediate', 'advanced'}
AUDIO_EXTENSIONS = {'.mp3', '.wav', '.ogg', '.m4a'}
IMAGE_EXTENSIONS = {'.svg', '.png', '.jpg', '.jpeg', '.webp'}
PACK_WRAPPER = re.compile(
    r'\s*window\.SHIFT_PACKS\s*=\s*window\.SHIFT_PACKS\s*\|\|\s*\[\s*\]\s*;'
    r'\s*window\.SHIFT_PACKS\.push\((.*)\)\s*;\s*\Z', re.S)
CATALOG_WRAPPER = re.compile(
    r'\s*window\.SHIFT_CATALOG\s*=\s*(\{.*\})\s*;'
    r'\s*window\.SHIFT_PACKS\s*=\s*window\.SHIFT_PACKS\s*\|\|\s*\[\s*\]\s*;\s*\Z', re.S)


class PackError(ValueError):
    """可直接顯示給作者的驗證訊息。"""


def require(condition, message):
    if not condition:
        raise PackError(message)


def safe_id(value):
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value)) and value not in FORBIDDEN_KEYS


def text(value, label):
    require(isinstance(value, str) and bool(value.strip()), f'{label} 必須是非空白文字。')
    return value


def integer(value):
    return isinstance(value, int) and not isinstance(value, bool)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, f'JSON 物件有重複欄位：{key}')
        require(key not in FORBIDDEN_KEYS, f'JSON 不接受此欄位名稱：{key}')
        result[key] = value
    return result


def reject_constant(value):
    raise PackError(f'JSON 不接受非有限數值：{value}')


def finite_float(value):
    result = float(value)
    require(math.isfinite(result), f'JSON 數值超出可接受範圍：{value}')
    return result


def parse_json(source, label):
    try:
        return json.loads(source, object_pairs_hook=unique_object, parse_constant=reject_constant, parse_float=finite_float)
    except json.JSONDecodeError as error:
        raise PackError(f'{label} JSON 格式錯誤：第 {error.lineno} 行、第 {error.colno} 欄。') from error


class LiteralParser:
    """只讀取舊版目錄的物件、陣列及基本值，不支援函式或運算式。"""

    def __init__(self, source):
        self.source = source
        self.pos = 0

    def skip(self):
        while self.pos < len(self.source) and self.source[self.pos].isspace():
            self.pos += 1

    def take(self, token):
        self.skip()
        require(self.source.startswith(token, self.pos), f'目錄格式錯誤：位置 {self.pos} 預期為 {token}。')
        self.pos += len(token)

    def string(self):
        quote = self.source[self.pos]
        self.pos += 1
        result = []
        escapes = {'n': '\n', 'r': '\r', 't': '\t', 'b': '\b', 'f': '\f', '\\': '\\', '/': '/', "'": "'", '"': '"'}
        while self.pos < len(self.source):
            char = self.source[self.pos]
            self.pos += 1
            if char == quote:
                return ''.join(result)
            require(ord(char) >= 32, '目錄字串不可含未跳脫的控制字元。')
            if char == '\\':
                require(self.pos < len(self.source), '目錄字串的跳脫字元不完整。')
                char = self.source[self.pos]
                self.pos += 1
                if char == 'u':
                    digits = self.source[self.pos:self.pos + 4]
                    require(bool(re.fullmatch(r'[0-9a-fA-F]{4}', digits)), '目錄的 Unicode 跳脫格式錯誤。')
                    result.append(chr(int(digits, 16)))
                    self.pos += 4
                else:
                    require(char in escapes, '目錄含不支援的字串跳脫。')
                    result.append(escapes[char])
            else:
                result.append(char)
        raise PackError('目錄字串沒有結束引號。')

    def value(self):
        self.skip()
        require(self.pos < len(self.source), '目錄內容未完成。')
        char = self.source[self.pos]
        if char in "\"'":
            return self.string()
        if char == '{':
            self.pos += 1
            pairs = []
            self.skip()
            if self.source.startswith('}', self.pos):
                self.pos += 1
                return {}
            while True:
                self.skip()
                require(self.pos < len(self.source), '目錄物件未完成。')
                if self.source[self.pos] in "\"'":
                    key = self.string()
                else:
                    match = re.match(r'[A-Za-z_$][A-Za-z0-9_$]*', self.source[self.pos:])
                    require(match is not None, '目錄欄位名稱格式錯誤。')
                    key = match.group()
                    self.pos += len(key)
                self.take(':')
                pairs.append((key, self.value()))
                self.skip()
                if self.source.startswith('}', self.pos):
                    self.pos += 1
                    return unique_object(pairs)
                self.take(',')
        if char == '[':
            self.pos += 1
            result = []
            self.skip()
            if self.source.startswith(']', self.pos):
                self.pos += 1
                return result
            while True:
                result.append(self.value())
                self.skip()
                if self.source.startswith(']', self.pos):
                    self.pos += 1
                    return result
                self.take(',')
        for literal, value in [('true', True), ('false', False), ('null', None)]:
            if self.source.startswith(literal, self.pos):
                self.pos += len(literal)
                return value
        match = re.match(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?', self.source[self.pos:])
        require(match is not None, '目錄只允許資料值，不接受函式或運算式。')
        self.pos += len(match.group())
        return parse_json(match.group(), '目錄數值')

    def parse(self):
        result = self.value()
        self.skip()
        require(self.pos == len(self.source), '目錄資料後含不支援的程式碼。')
        return result


def relative_file(root, value, label, prefixes, extensions, must_exist=True):
    text(value, label)
    require(bool(re.fullmatch(r'[A-Za-z0-9_./-]+', value)), f'{label} 必須使用英文檔名的安全相對路徑。')
    parts = value.split('/')
    require(len(parts) >= 2 and parts[0] in prefixes and all(p not in ('', '.', '..') for p in parts),
            f'{label} 必須位於 {"/ 或 ".join(prefixes)}/，不得使用絕對路徑或上層目錄。')
    require('..' not in value, f'{label} 不得包含連續兩個句點。')
    require(Path(value).suffix in extensions, f'{label} 的副檔名不受支援。')
    candidate = root.joinpath(*parts)
    require(candidate.resolve().is_relative_to(root), f'{label} 不得指向網站資料夾以外。')
    if must_exist:
        require(candidate.is_file(), f'{label} 找不到檔案：{value}；請先放進網站資料夾。')
    return candidate


def validate_pack(pack, root):
    require(isinstance(pack, dict), '題庫最外層必須是一個 JSON 物件。')
    require(integer(pack.get('schemaVersion')) and pack['schemaVersion'] == 1, 'schemaVersion 必須是 1。')
    pack_id = pack.get('testId')
    require(isinstance(pack_id, str) and bool(PACK_ID_PATTERN.fullmatch(pack_id)) and pack_id not in FORBIDDEN_KEYS,
            'testId 請使用 1～64 個英文字母、數字、連字號或底線，開頭須為英數字。')
    require(not re.fullmatch(r'(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])', pack_id, re.I), 'testId 不得使用作業系統保留名稱。')
    require(isinstance(pack.get('groups'), list), 'groups 必須是陣列，無題組時填入 []。')
    require(isinstance(pack.get('questions'), list) and 1 <= len(pack['questions']) <= LIMIT_QUESTIONS,
            f'每個題庫須包含 1～{LIMIT_QUESTIONS:,} 題。')
    for key in ('title', 'subtitle'):
        if key in pack:
            text(pack[key], key)
    groups = {}
    for group in pack['groups']:
        require(isinstance(group, dict) and safe_id(group.get('id')), '題組必須有有效的 id。')
        gid = group['id']
        require(gid not in groups, f'題組 ID 重複：{gid}')
        require(group.get('testId') == pack_id, f'{gid} 的 testId 必須等於 {pack_id}。')
        require(integer(group.get('part')) and 1 <= group['part'] <= 7, f'{gid} 的 part 必須為 1～7。')
        require(group.get('topic') in TOPICS, f'{gid} 的 topic 不受支援。')
        for field in ('title', 'titleZh', 'passage', 'passageZh'):
            text(group.get(field), f'{gid}.{field}')
        if group['part'] <= 4:
            require(bool(group.get('audio')), f'聽力題組 {gid} 必須提供 audio 音檔路徑。')
        if group['part'] == 1:
            require(bool(group.get('image')), f'Part 1 題組 {gid} 必須提供 image 圖片路徑。')
        if group.get('audio') is not None:
            relative_file(root, group['audio'], f'{gid}.audio', {'audio'}, AUDIO_EXTENSIONS)
        if group.get('image') is not None:
            relative_file(root, group['image'], f'{gid}.image', {'assets'}, IMAGE_EXTENSIONS)
        if 'duration' in group:
            duration = group['duration']
            require(isinstance(duration, (int, float)) and not isinstance(duration, bool) and math.isfinite(duration) and duration >= 0,
                    f'{gid}.duration 必須為非負、有限的秒數。')
        if 'audioScript' in group:
            text(group['audioScript'], f'{gid}.audioScript')
        if 'turns' in group:
            require(isinstance(group['turns'], list) and bool(group['turns']), f'{gid}.turns 必須是非空陣列。')
            for turn in group['turns']:
                require(isinstance(turn, dict) and turn.get('voice') in ('female', 'male'), f'{gid} 的 voice 必須為 female 或 male。')
                text(turn.get('text'), f'{gid}.turns.text')
        groups[gid] = group
    question_ids = set()
    numbers = set()
    referenced = set()
    for question in pack['questions']:
        require(isinstance(question, dict) and safe_id(question.get('id')), '每題必須有有效的 id。')
        qid = question['id']
        require(qid not in question_ids and qid not in groups, f'題目／題組 ID 重複：{qid}')
        require(question.get('testId') == pack_id, f'{qid} 的 testId 必須等於 {pack_id}。')
        part = question.get('part')
        require(integer(part) and 1 <= part <= 7, f'{qid} 的 part 必須為 1～7。')
        number = question.get('number')
        require(integer(number) and 1 <= number <= 9007199254740991 and number not in numbers, f'{qid} 的 number 必須是題庫內不重複的正整數。')
        require(question.get('topic') in TOPICS, f'{qid} 的 topic 不受支援。')
        require(question.get('difficulty') in DIFFICULTIES, f'{qid} 的 difficulty 不受支援。')
        for field in ('prompt', 'promptZh', 'explanationZh', 'evidence'):
            text(question.get(field), f'{qid}.{field}')
        gid = question.get('groupId')
        if gid is not None:
            require(safe_id(gid) and gid in groups, f'{qid} 引用的 groupId 不存在。')
            require(groups[gid]['part'] == part, f'{qid} 與題組的 Part 不一致。')
            referenced.add(gid)
        else:
            require(part == 5, f'{qid} 不是 Part 5，必須引用完整題組。')
        tags = question.get('tags')
        require(isinstance(tags, list) and all(isinstance(tag, str) and tag.strip() for tag in tags), f'{qid}.tags 必須是文字陣列，可填 []。')
        expected = list('ABC' if part == 2 else 'ABCD')
        options = question.get('options')
        require(isinstance(options, list) and len(options) == len(expected), f'{qid} 必須有 {len(expected)} 個選項。')
        require(all(isinstance(option, dict) for option in options), f'{qid} 的選項必須是物件。')
        require([option.get('id') for option in options] == expected, f'{qid} 的選項 ID 必須依序為 {"、".join(expected)}。')
        for option in options:
            for field in ('text', 'zh', 'whyZh'):
                text(option.get(field), f'{qid}.{option["id"]}.{field}')
        require(len({option['text'].strip() for option in options}) == len(expected), f'{qid} 有內容重複的選項。')
        require(question.get('answer') in expected, f'{qid} 的 answer 必須對應一個現有選項。')
        vocabulary = question.get('vocabulary')
        require(isinstance(vocabulary, list) and bool(vocabulary), f'{qid}.vocabulary 至少需要一個詞彙。')
        for item in vocabulary:
            require(isinstance(item, dict), f'{qid} 的詞彙必須是物件。')
            for field in ('term', 'zh', 'note'):
                text(item.get(field), f'{qid}.vocabulary.{field}')
        question_ids.add(qid)
        numbers.add(number)
    require(referenced == set(groups), 'groups 中有未被任何題目引用的題組，請移除或補上題目。')
    return question_ids | set(groups)


def load_catalog(root):
    path = root / 'data' / 'catalog.js'
    require(path.is_file(), '找不到 data/catalog.js；--site-dir 必須指向含 index.html 的網站根目錄。')
    require(not path.is_symlink() and path.resolve().is_relative_to(root), 'catalog.js 不得是指向其他位置的符號連結。')
    source = path.read_text(encoding='utf-8-sig')
    match = CATALOG_WRAPPER.fullmatch(source)
    require(match is not None, 'catalog.js 不符合 SHIFT_CATALOG／SHIFT_PACKS 的標準包裝格式。')
    catalog = LiteralParser(match.group(1)).parse()
    require(isinstance(catalog, dict) and isinstance(catalog.get('tests'), list), '目錄須包含 tests 陣列。')
    seen = set()
    paths = set()
    for entry in catalog['tests']:
        require(isinstance(entry, dict) and safe_id(entry.get('id')), '目錄含無效題庫 ID。')
        require(entry['id'].casefold() not in seen, f'目錄有重複題庫 ID：{entry["id"]}')
        seen.add(entry['id'].casefold())
        relative_file(root, entry.get('path'), f'{entry["id"]} 題庫檔', {'data'}, {'.js'})
        require(entry['path'].casefold() not in paths, '目錄有多個項目指向同一個題庫檔。')
        paths.add(entry['path'].casefold())
    return catalog, path


def existing_ids(catalog, root, replacing_id):
    owners = {}
    for entry in catalog['tests']:
        script = relative_file(root, entry['path'], '既有題庫', {'data'}, {'.js'}).read_text(encoding='utf-8-sig')
        match = PACK_WRAPPER.fullmatch(script)
        require(match is not None, f'{entry["path"]} 不是支援的 SHIFT_PACKS 包裝格式。')
        pack = parse_json(match.group(1), entry['path'])
        require(isinstance(pack, dict) and pack.get('testId') == entry['id'], f'{entry["path"]} 的 testId 與目錄不符。')
        if entry['id'] == replacing_id:
            continue
        for field in ('questions', 'groups'):
            require(isinstance(pack.get(field), list), f'{entry["path"]} 缺少 {field}。')
            for record in pack[field]:
                require(isinstance(record, dict) and safe_id(record.get('id')), f'{entry["path"]} 有無效 ID。')
                rid = record['id']
                require(rid not in owners, f'既有題庫已有重複 ID：{rid}')
                owners[rid] = entry['id']
    return owners


def js_json(value):
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':')).replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029')


def atomic_write(path, content):
    require(not path.is_symlink(), f'輸出目標不得是符號連結：{path.name}')
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o644
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', suffix='.tmp', dir=str(path.parent))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description='驗證 JSON，產生可直接開檔使用的 JS 題庫並更新首頁目錄。')
    parser.add_argument('json_file', help='UTF-8 JSON 題庫檔案')
    parser.add_argument('--site-dir', type=Path, default=Path(__file__).resolve().parent.parent, help='網站根目錄；預設為此工具所屬網站')
    parser.add_argument('--title', help='首頁題庫標題；預設採 JSON 的 title 或 testId')
    parser.add_argument('--subtitle', help='首頁副標題；預設採 JSON 的 subtitle 或「自訂擴充題庫」')
    parser.add_argument('--replace', action='store_true', help='更新同 ID 的既有擴充題庫；不允許覆蓋內建 test-01／test-02')
    parser.add_argument('--check', action='store_true', help='只驗證，不寫入任何檔案')
    args = parser.parse_args(argv)
    root = args.site_dir.resolve()
    require(root.is_dir() and (root / 'index.html').is_file(), '網站根目錄必須包含 index.html。')
    source = Path(args.json_file).resolve()
    require(source.is_file(), f'找不到 JSON 檔案：{source}')
    require(source.stat().st_size <= LIMIT_BYTES, '題庫超過 20 MiB，請先拆成較小的題庫包。')
    pack = parse_json(source.read_text(encoding='utf-8-sig'), source.name)
    if args.title is not None:
        pack['title'] = text(args.title, '--title')
    if args.subtitle is not None:
        pack['subtitle'] = text(args.subtitle, '--subtitle')
    candidate_ids = validate_pack(pack, root)
    pack_id = pack['testId']
    require(pack_id not in BUILTIN_IDS, '工具保留內建 test-01／test-02，請使用新的 testId。')
    catalog, catalog_path = load_catalog(root)
    matches = [entry for entry in catalog['tests'] if entry['id'].casefold() == pack_id.casefold()]
    old_entry = matches[0] if matches else None
    if old_entry:
        require(old_entry['id'] == pack_id, 'testId 與既有題庫只差大小寫，請改用不同 ID。')
        require(args.replace, f'{pack_id} 已存在；若確實要更新，請加上 --replace。')
    else:
        require(not args.replace, '--replace 只適用於目錄中已存在的擴充題庫；新增題庫請移除此參數。')
    owners = existing_ids(catalog, root, pack_id if old_entry else None)
    overlap = sorted(candidate_ids & owners.keys())
    require(not overlap, '題目或題組 ID 已被其他題庫使用：' + ', '.join(overlap[:8]))
    output_relative = old_entry['path'] if old_entry else f'data/{pack_id}.js'
    output = relative_file(root, output_relative, '輸出題庫', {'data'}, {'.js'}, must_exist=False)
    require(old_entry is not None or not output.exists(), f'{output_relative} 已存在但未登錄；請先另存或更換 testId。')
    require(not output.is_symlink(), '輸出題庫不得是符號連結。')
    questions = pack['questions']
    entry = {'id': pack_id, 'title': pack.get('title', pack_id), 'subtitle': pack.get('subtitle', '自訂擴充題庫'),
             'reading': sum(q['part'] > 4 for q in questions), 'listening': sum(q['part'] <= 4 for q in questions),
             'path': output_relative, 'topics': sorted({q['topic'] for q in questions})}
    catalog['tests'] = [entry if item['id'] == pack_id else item for item in catalog['tests']] if old_entry else catalog['tests'] + [entry]
    pack_bytes = ('window.SHIFT_PACKS=window.SHIFT_PACKS||[];window.SHIFT_PACKS.push(' + js_json(pack) + ');\n').encode('utf-8')
    catalog_bytes = ('window.SHIFT_CATALOG=' + js_json(catalog) + ';\nwindow.SHIFT_PACKS=window.SHIFT_PACKS||[];\n').encode('utf-8')
    if args.check:
        print(f'檢查通過：{pack_id}，閱讀 {entry["reading"]} 題、聽力 {entry["listening"]} 題；未變更檔案。')
        return 0
    old_bytes = output.read_bytes() if output.exists() else None
    atomic_write(output, pack_bytes)
    try:
        atomic_write(catalog_path, catalog_bytes)
    except (OSError, PackError) as error:
        try:
            if old_bytes is None:
                output.unlink()
            else:
                atomic_write(output, old_bytes)
        except (OSError, PackError) as rollback:
            raise PackError(f'目錄更新失敗，且題庫還原失敗：{rollback}；請從備份還原 data 目錄。') from error
        raise PackError('目錄更新失敗；已還原本次題庫檔案變更。') from error
    print(f'已{"更新" if old_entry else "新增"}：{output_relative}')
    print(f'已更新：data/catalog.js；閱讀 {entry["reading"]} 題、聽力 {entry["listening"]} 題。')
    print('重新整理或重新開啟 index.html，即可在首頁選擇此題庫。HTML 無須修改。')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (PackError, OSError, UnicodeError, RecursionError, TypeError) as error:
        print(f'無法加入題庫：{error}', file=sys.stderr)
        raise SystemExit(1)
