import sys
for stream in (sys.stdin, sys.stdout, sys.stderr):
    if stream is not None and hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='replace')

def main():
    if '--settings' in sys.argv:
        import key_settings
        key_settings.main()
    else:
        import soundboard
        soundboard.main()

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'启动失败：{error}', flush=True)
        if '--self-test' not in sys.argv:
            input('按回车关闭窗口……')
        sys.exit(1)

