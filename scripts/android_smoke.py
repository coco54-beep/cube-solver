"""ADB test helper: capture screens and scoped logs without clearing app data."""
import argparse
import json
import subprocess
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--adb',required=True)
    parser.add_argument('--serial',required=True)
    parser.add_argument('--output',default='reports/android-test/1.2.21')
    parser.add_argument('action',choices=('capture','tap','swipe','key','log'))
    parser.add_argument('args',nargs='*')
    options=parser.parse_args()
    output=Path(options.output)
    output.mkdir(parents=True,exist_ok=True)
    def adb(*args):
        return subprocess.run([options.adb,'-s',options.serial,*args],check=True,capture_output=True)
    if options.action=='capture':
        destination=output/(options.args[0]+'.png')
        destination.write_bytes(adb('exec-out','screencap','-p').stdout)
        print(destination.resolve())
    elif options.action=='log':
        pid=adb('shell','pidof','com.example.cubesolver').stdout.decode().strip()
        destination=output/(options.args[0]+'.log')
        destination.write_bytes(adb('logcat','-d','--pid='+pid).stdout)
        print(destination.resolve())
    else:
        adb('shell','input','keyevent' if options.action=='key' else options.action,*options.args)
    if options.action in ('tap','swipe','key'):
        with (output/'actions.jsonl').open('a',encoding='utf8') as stream:
            stream.write(json.dumps({'action':options.action,'args':options.args})+'\n')


if __name__=='__main__':
    main()
