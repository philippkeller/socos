#!/usr/bin/env python

from __future__ import print_function


""" socos is a commandline tool for controlling Sonos speakers """

# Will be parsed by setup.py to determine package metadata
__author__ = 'SoCo team <python-soco @googlegroups.com>'
__version__ = '0.1'
__website__ = 'https://github.com/SoCo/socos'
__license__ = 'MIT License'


import sys
import shlex

try:
    import colorama
except:
    colorama = False

try:
    import readline
except:
    readline = None

try:
    input = raw_input
except NameError:
    # raw_input has been renamed to input in Python 3
    pass

import soco

# current speaker (used only in interactive mode)
CUR_SPEAKER = None


def main():
    name = sys.argv[0]
    args = sys.argv[1:]

    if args:
        # process command and exit
        process_cmd(name, args)
    else:
        # start interactive shell
        shell()


def process_cmd(name, args):
    """ Processes a single command """

    cmd = args.pop(0).lower()

    if cmd not in COMMANDS:
        err('Unknown command "{cmd}"'.format(cmd=cmd))
        err(get_help())
        return False

    req_ip, func = COMMANDS[cmd]

    # check if we operate on a spectifc speaker / group
    if req_ip:
        if not CUR_SPEAKER:
            if not args:
                err('Please specify a speaker IP for "{cmd}".'.format(cmd=cmd))
                return
            else:
                speaker_spec = args.pop(0)
                sonos = soco.SoCo(speaker_spec)
                args.insert(0, sonos)
        else:
            args.insert(0, CUR_SPEAKER)

    # determine how to call function
    if isinstance(func, str):
        sonos = args.pop(0)
        method = getattr(sonos, func)
        result = method(*args)

    else:
        try:
            result = func(*args)
        except TypeError as ex:
            err(ex)
            return

    # colorama.init() takes over stdout/stderr to give cross-platform colors
    if colorama:
        colorama.init()

    # process output
    if result is None:
        pass

    elif hasattr(result, '__iter__'):
        for line in result:
            print(line)

    else:
        print(result)

    # Release stdout/stderr from colorama
    if colorama:
        colorama.deinit()


def shell():
    """ Start an interactive shell """

    if readline is not None:
        readline.parse_and_bind('tab: complete')
        readline.set_completer(complete_command)
        readline.set_completer_delims(' ')

    while True:
        try:
            if CUR_SPEAKER:
                line = input('socos({speaker})> '.format(
                    speaker=CUR_SPEAKER.player_name).encode('utf-8'))
            else:
                line = input('socos> ')
        except EOFError:
            print('')
            break
        except KeyboardInterrupt:
            print('')
            continue

        line = line.strip()
        if not line:
            continue

        try:
            args = shlex.split(line)
        except ValueError as value_error:
            err('Syntax error: %(error)s' % {'error': value_error})
            continue

        try:
            process_cmd('', args)
        except KeyboardInterrupt:
            err('Keyboard interrupt.')
        except EOFError:
            err('EOF.')


def complete_command(text, context):
    """ auto-complete commands

    text is the text to be auto-completed
    context is an index, increased for every call for "text" to get next match
    """
    matches = list(filter(lambda k: k.startswith(text), COMMANDS.keys()))
    return matches[context]


def adjust_volume(sonos, operator):
    """ Adjust the volume up or down with a factor from 1 to 100 """
    factor = get_volume_adjustment_factor(operator)
    if not factor:
        return False

    volume = sonos.volume

    if (operator[0] == '+'):
        if (volume + factor) > 100:
            factor = 1
        sonos.volume = (volume + factor)
        return sonos.volume
    elif (operator[0] == '-'):
        if (volume - factor) < 0:
            factor = 1
        sonos.volume = (volume - factor)
        return sonos.volume
    else:
        err("Valid operators for volume are + and -")


def get_volume_adjustment_factor(operator):
    """ get the factor to adjust the volume with """
    factor = 1
    if len(operator) > 1:
        try:
            factor = int(operator[1:])
        except ValueError:
            err("Adjustment factor for volume has to be a int.")
            return
    return factor


def get_current_track_info(sonos):
    """ Show the current track """
    track = sonos.get_current_track_info()
    return (
        "Current track: %s - %s. From album %s. This is track number"
        " %s in the playlist. It is %s minutes long." % (
            track['artist'],
            track['title'],
            track['album'],
            track['playlist_position'],
            track['duration'],
        )
    )


def get_queue(sonos):
    """ Show the current queue """
    queue = sonos.get_queue()

    ANSI_BOLD = '\033[1m'
    ANSI_RESET = '\033[0m'

    current = int(sonos.get_current_track_info()['playlist_position'])

    queue_length = len(queue)
    padding = len(str(queue_length))

    for idx, track in enumerate(queue, 1):
        if (idx == current):
            color = ANSI_BOLD
        else:
            color = ANSI_RESET

        idx = str(idx).rjust(padding)
        yield (
            "%s%s: %s - %s. From album %s." % (
                color,
                idx,
                track['artist'],
                track['title'],
                track['album'],
            )
        )


def err(s):
    print(s, file=sys.stderr)


def play_index(sonos, index):
    """ Play an item from the playlist """
    queue_length = len(sonos.get_queue())
    try:
        index = int(index) - 1
        if index >= 0 and index < queue_length:
            current = int(sonos.get_current_track_info()['playlist_position']) - 1
            if (index != current):
                return sonos.play_from_queue(index)
        else:
            raise ValueError()
    except ValueError():
        return "Index has to be a integer within the range 1 - %d" % queue_length


def list_ips():
    """ List available devices """
    sonos = soco.SonosDiscovery()
    return sonos.get_speaker_ips()


def speaker_info(sonos):
    """ Information about a speaker """
    infos = sonos.get_speaker_info()
    return ('%s: %s' % (i, infos[i]) for i in infos)


def volume(sonos, *args):
    """ Change or show the volume of a device """
    if args:
        operator = args[0].lower()
        adjust_volume(sonos, operator)

    return sonos.volume


def exit():
    """ Exit socos """
    sys.exit(0)


def play(sonos, *args):
    """ Start playing """
    if args:
        idx = args[0]
        play_index(sonos, idx)
    else:
        sonos.play()
    return get_current_track_info(sonos)


def play_next(sonos):
    """ Play the next track """
    sonos.next()
    return get_current_track_info(sonos)


def play_previous(sonos):
    """ Play the previous track """
    sonos.previous()
    return get_current_track_info(sonos)


def state(sonos):
    """ Get the current state of a device / group """
    return sonos.get_current_transport_info()['current_transport_state']


def set_speaker(ip):
    """ set the current speaker for the shell session """
    global CUR_SPEAKER
    CUR_SPEAKER = soco.SoCo(ip)


def unset_speaker():
    """ resets the current speaker for the shell session """
    global CUR_SPEAKER
    CUR_SPEAKER = None


def get_help():
    """ Prints a list of commands with short description """

    def _cmd_summary(item):
        """ Format command name and first line of docstring """
        name, func = item[0], item[1][1]
        if isinstance(func, str):
            func = getattr(soco.SoCo, func)
        doc = getattr(func, '__doc__') or ''
        doc = doc.split('\n')[0]
        return ' * {cmd:10s} {doc}'.format(cmd=name, doc=doc)

    texts = ['Available commands:']
    texts += map(_cmd_summary, COMMANDS.items())
    return '\n'.join(texts)


# COMMANDS indexes commands by their name. Each command is a 2-tuple of
# (requires_ip, function) where function is either a callable, or a
# method name to be called on a SoCo instance (depending on requires_ip)
# If requires_ip is False, function must be a callable.
COMMANDS = {
    #  cmd         req IP  func
    'list':       (False, list_ips),
    'partymode':  (True,  'partymode'),
    'info':       (True,  speaker_info),
    'play':       (True,  play),
    'pause':      (True,  'pause'),
    'stop':       (True,  'stop'),
    'next':       (True,  play_next),
    'previous':   (True,  play_previous),
    'current':    (True,  get_current_track_info),
    'queue':      (True,  get_queue),
    'volume':     (True,  volume),
    'state':      (True,  state),
    'exit':       (False, exit),
    'set':        (False, set_speaker),
    'unset':      (False, unset_speaker),
    'help':       (False, get_help),
}


if __name__ == '__main__':
    main()