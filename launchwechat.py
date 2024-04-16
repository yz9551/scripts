#!/usr/bin/env python3
import subprocess
import time
import socket
import os
import sys


def match_head(head):
    return lambda title: title.startswith(head)


RUN_WECHAT_CMD = ('steam', 'steam://rungameid/14783848130939977728')
KILL_WECHAT_CMD = ('pkill', 'WeChat.exe')
GET_WINDOW_CMD = ('xwininfo', '-root', '-children')
HIDE_WINDOW_CMD = ['xdotool', 'windowunmap']
WECHAT_WINDOW_NAMES = (
    'Chat Info',
    'Weixin',
    'Chat Files',
    'Moments',
    'EmotionView',
    'AddMemberWnd',
    'Settings',
    'Weixin for Windows Update',
    'EmotionTipWnd',
    'Backup and Restore',
    '登录',
    'has no name',
    match_head('Chat History for '),
)
# the range of increase in size to count as a shadow
BORDER_EXTRA_MIN = 10
BORDER_EXTRA_MAX = 50
TOTAL_SHADOW_COUNT = 20


def parse(line):
    name = []
    length = 0
    for word in line[1:]:
        name.append(word)
        if word.find('":') == len(word) - 2 or word.find('):') == len(word) - 2:
            length = line.index(word)
            break
    # print('[Debug] parse: Got line', line, 'length:', length)
    line = [line[0], ' '.join(name), *line[length + 1:]]
    return line


def remove_shadow(unmapped_ids=[]):
    # Run xwininfo to get open windows
    try:
        process = subprocess.Popen(GET_WINDOW_CMD,
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        output, error = process.communicate()

        if error:
            print("Error:", error.decode("utf-8"))

        result = output.decode("utf-8").strip().split('\n')[5:]

    except Exception as e:
        print("An error occurred:", e)

    new_result = []
    for line in result:
        if 'steam_app_0' in line:
            new_result.append(parse(line.strip().split()))
    result = new_result

    for line in result:
        pass
        # print('[Debug] Open window', line)
    # exit()

    wechat_window_size = []
    for line in result:
        # print(repr(line))
        window_title = line[1][1:-2]
        for wechat_window in WECHAT_WINDOW_NAMES:
            if type(wechat_window) is str and window_title == wechat_window\
                    or wechat_window(window_title):
                print('[Info] Found wechat window', line)
                wechat_window_size.append(line[4].split('+')[0].split('x'))

    # print(wechat_window_size)
    shadow_window_ids = []

    for line in result:
        if line[1:4] != ['(has no name):', '("steam_app_0"', '"steam_app_0")']:
            continue
        size = line[4].split('+')[0].split('x')
        for window_size in wechat_window_size:
            if int(window_size[0]) + BORDER_EXTRA_MIN <= int(size[0]) <= int(window_size[0]) + BORDER_EXTRA_MAX\
                    and int(window_size[1]) + BORDER_EXTRA_MIN <= int(size[1]) <= int(window_size[1]) + BORDER_EXTRA_MAX:
                print('[Info] Found wechat shadow', line)
                shadow_window_ids.append(line[0])

    for window_id in shadow_window_ids:
        unmapped_ids.append(window_id)
        try:
            process = subprocess.Popen(
                [*HIDE_WINDOW_CMD, str(window_id)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
            output, error = process.communicate()

            if error:
                print("Error:", error.decode("utf-8"))

            if output:
                print("[xdotool]", output.decode("utf-8"))

        except Exception as e:
            print("An error occurred:", e)


def launch_wechat():
    try:
        subprocess.run(KILL_WECHAT_CMD)
        time.sleep(0.4)
        subprocess.run(RUN_WECHAT_CMD)
        time.sleep(2)

    except Exception as e:
        print("An error occurred:", e)


def handle_hyprland_ipc(message):
    print('[Info] Got hyprland ipc', message)
    if message.split(',')[1] in WECHAT_WINDOW_NAMES:
        remove_shadow()


def watch_new_window():
    # connect to hyprland and remove any new shadows that spawn with new windows
    HYPRLAND_INSTANCE_SIGNATURE = os.getenv("HYPRLAND_INSTANCE_SIGNATURE")
    hyprland_socket_path = f'/tmp/hypr/{HYPRLAND_INSTANCE_SIGNATURE}/.socket2.sock'

    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as hyprland_socket:
        hyprland_socket.connect(hyprland_socket_path)

        record_buffer = ''
        while True:
            received_data = hyprland_socket.recv(1024).decode('utf-8')
            if not received_data:
                break
            records = (record_buffer + received_data).split('\n')
            if received_data[-1] != '\n':
                record_buffer = records.pop()  # Store incomplete record for future processing
            else:
                record_buffer = ''
            for record in records:
                # print('[Debug] Got hyprland ipc', record)
                if record.startswith('activewindow>>'):
                    handle_hyprland_ipc(record.strip())


if __name__ == '__main__':
    if '--new' in sys.argv:
        launch_wechat()
        unmapped_ids = [1, 2]
        # hide the two main shadows
        while len(unmapped_ids) < TOTAL_SHADOW_COUNT:
            time.sleep(0.3)
            remove_shadow(unmapped_ids)
        # TODO: fix hyprland ipc closing Chat Info
    if '--loop' in sys.argv:
        watch_new_window()
    if len(sys.argv) == 1:
        remove_shadow()

