import json
from pathlib import Path
from app_paths import ROOT

CONFIG = ROOT / '其他' / '按键设置.json'
DEFAULTS = {'jet': 'X', 'c4': 'G', 'cannon': 'Z', 'toggle': '0'}
LABELS = {'jet': '喷气', 'c4': 'C4', 'cannon': '虎蹲炮', 'toggle': '全部功能开关'}
SPECIAL = {'SPACE':32, 'TAB':9, 'ENTER':13, 'ESC':27, 'BACKSPACE':8,
           'INSERT':45, 'DELETE':46, 'HOME':36, 'END':35, 'PAGEUP':33,
           'PAGEDOWN':34, 'UP':38, 'DOWN':40, 'LEFT':37, 'RIGHT':39}
ALIASES = {'空格':'SPACE', '回车':'ENTER', 'ESCAPE':'ESC', 'DEL':'DELETE',
           'INS':'INSERT', 'PGUP':'PAGEUP', 'PGDN':'PAGEDOWN'}
RESERVED = {49,50,51,97,98,99,187,189,107,109}

def parse_key(value):
    name = ALIASES.get(str(value).strip().upper(), str(value).strip().upper())
    if len(name) == 1 and ('A' <= name <= 'Z' or '0' <= name <= '9'):
        codes = {ord(name)}
        if name == '0': codes.add(96)  # preserve both zero keys
    elif name in SPECIAL:
        codes = {SPECIAL[name]}
    elif name.startswith('F') and name[1:].isdigit() and 1 <= int(name[1:]) <= 24:
        name = 'F' + str(int(name[1:])); codes = {111 + int(name[1:])}
    elif name.startswith('NUM') and len(name) == 4 and name[-1].isdigit():
        codes = {96 + int(name[-1])}
    else:
        raise ValueError('请输入单个字母、数字、F1–F24，或 SPACE/TAB 等按键名称；不支持组合键。')
    if codes & RESERVED:
        raise ValueError('1、2、3 和 +/- 已用于音乐及音量，请选其他按键。')
    return name, codes

def validate(settings):
    if not isinstance(settings, dict) or set(settings) != set(DEFAULTS):
        raise ValueError('设置必须包含喷气、C4、虎蹲炮、总开关四项。')
    normalized = {}; used = set()
    for action in DEFAULTS:
        name, codes = parse_key(settings[action])
        if used & codes:
            raise ValueError('四个功能不能使用相同按键（0 与 NUM0 也不能重复）。')
        used.update(codes); normalized[action] = name
    return normalized

def load_settings(path=CONFIG):
    if not path.exists(): return DEFAULTS.copy()
    try:
        return validate(json.loads(path.read_text(encoding='utf-8-sig')))
    except (ValueError, TypeError) as error:
        raise ValueError(f'按键设置无效，请运行根目录的设置.bat 修复：{error}') from error

def bindings(settings):
    result = {}
    for action, name in validate(settings).items():
        for code in parse_key(name)[1]: result[code] = action
    return result

def save_settings(settings, path=CONFIG):
    settings = validate(settings)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    temp.write_text(json.dumps(settings, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temp.replace(path)

def main():
    try:
        current = load_settings()
    except ValueError as error:
        print(error)
        current = DEFAULTS.copy()
    print('三角洲插件 · 按键设置')
    print('逐项输入按键名称，直接回车保留当前值。Ctrl+C 取消，不保存。')
    print('支持字母、数字、F1–F24、SPACE、TAB、NUM0 等；1/2/3 和 +/- 保留。')
    try:
        while True:
            proposed = {}
            for action, label in LABELS.items():
                while True:
                    answer = input(f'{label}按键 [{current[action]}]：').strip() or current[action]
                    try:
                        proposed[action] = parse_key(answer)[0]
                        break
                    except ValueError as error:
                        print(error)
            try:
                save_settings(proposed)
                break
            except ValueError as error:
                print(f'未保存：{error} 请重新填写。')
                current = proposed
        print('设置已保存。请关闭旧程序，再以管理员身份运行 启动程序.exe。')
    except (KeyboardInterrupt, EOFError):
        print('\n已取消，原设置未更改。')
