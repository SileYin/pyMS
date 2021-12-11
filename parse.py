import numpy as np
import glob
import os
import librosa
import random
import re
import soundfile as sf


def read_bms_file(filepath):
    try:
        file_data = open(filepath, 'r', encoding='utf-8')
        bms_string = file_data.readlines()
    except UnicodeDecodeError:
        file_data = open(filepath, 'r', encoding='shift_jis')
        bms_string = file_data.readlines()
    return bms_string


def parse_control_flow(bms_string):
    have_random = False
    for line in bms_string:
        command = line.split(' ')[0]
        command_val = line.split(' ')[-1]
        if command == '#RAMDOM':
            have_random = True
            random_value = random.randint(1, command_val)
            bms_string.remove(line)
            in_if_block = False
            if_val = False
        if have_random:
            if command == '#IF':
                in_if_block = True
                if command_val == random_value:
                    if_val = True
                else:
                    if_val = False
                bms_string.remove(line)
            elif command == '#ENDIF':
                in_if_block = False
                if_val = False
                bms_string.remove(line)
            else:
                if in_if_block and not if_val:
                    bms_string.remove(line)
    return


class BMSHeader:
    def __init__(self, bms_string):
        header_matcher = re.compile(
            r'#(?P<command>\w+)(?:\s+(?P<value>\S.*))?$',
            re.IGNORECASE
        )
        self.bpm_list = np.empty(36 ** 2)
        self.use_bpm_list = False
        for line in bms_string:
            matched = header_matcher.match(line)
            if matched:
                command = matched.group('command')
                value = matched.group('value')
                if command == 'PLAYER':
                    self.mode = value
                elif command == 'RANK':
                    self.judge = value
                elif command == 'TOTAL':
                    self.total = value
                elif command == 'STAGEFILE':
                    self.stage_file = value
                elif command == 'PLAY LEVEL':
                    self.level = value
                elif command == 'DIFFICULTY':
                    self.difficulty = value
                elif command == 'TITLE':
                    self.title = value
                elif command == 'SUBTITLE':
                    self.subtitle = value
                elif command == 'ARTIST':
                    self.artist = value
                elif command == 'SUBARTIST':
                    self.subartist = value
                elif command == 'GENRE':
                    self.genre = value
                elif command == 'BPM':
                    self.bpm = value
                elif command.startswith('BPM'):
                    self.bpm_list[int(command[-2:], base=36)] = float(value)
                    self.use_bpm_list = True


class MediaObj:
    def __init__(self, bms_string, bms_path, type='WAV'):
        if type == 'WAV':
            matcher = re.compile(
                r'#(WAV)(?P<index>\S\S)\s(?P<file>\S.*)$',
                re.IGNORECASE
            )
        elif type == 'BMP':
            matcher = re.compile(
                r'#(BMP)(?P<index>\S\S)\s(?P<file>\S.*)$',
                re.IGNORECASE
            )
        self.media_list = [np.empty((2, 0)) for i in range(36 ** 2)]
        for line in bms_string:
            matched = matcher.match(line)
            if matched:
                media_idx = int(matched.group('index'), base=36)
                media_path = glob.glob(glob.escape(os.path.join(bms_path.split('/')[0],
                                                                matched.group('file').split('.')[0]))+'.*')[0]
                if type == 'WAV':
                    media, fs = librosa.load(media_path, sr=None, mono=False)
                    self.media_list[media_idx] = media
                    self.fs = fs


class BMSRawMeasure:
    def __init__(self, measure_number):
        self.measure_number = measure_number
        self.bgm = []
        self.beats = 4
        self.vary_bpm = False
        self.bpm_channel = []
        self.bga_channel = np.empty(0)
        self.note_channels = [np.empty(0) for i in range(8)]

    def edit_channel(self, channel, content):
        if channel == 1:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.bgm.append(content_value)
        elif channel == 2:
            self.beats = 4 * float(content)
        elif channel == 3:
            content_value = [content[i:i + 2] for i in range(0, len(content), 2)]
            self.vary_bpm = True
            self.bpm_channel = content_value
        elif channel == 4:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.bga_channel = content_value
        elif channel == 11:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.note_channels[0] = content_value
        elif channel == 12:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.note_channels[1] = content_value
        elif channel == 13:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.note_channels[2] = content_value
        elif channel == 14:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.note_channels[3] = content_value
        elif channel == 15:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.note_channels[4] = content_value
        elif channel == 18:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.note_channels[5] = content_value
        elif channel == 19:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.note_channels[6] = content_value
        elif channel == 16:
            content_value = np.array([int(content[i:i + 2], base=36) for i in range(0, len(content), 2)])
            self.note_channels[7] = content_value
        return


class BMSChannels:
    def __init__(self, bms_string):
        matcher = re.compile(
            r'^#(?:EXT\s+#)?(?P<measure>\d\d\d)(?P<channel>\S\S):(?P<content>\S*)$',
            re.IGNORECASE
        )
        self.measure_list = []
        cur_measure = BMSRawMeasure(0)
        for line in bms_string:
            matched = matcher.match(line)
            if matched:
                measure_idx = int(matched.group('measure'))
                channel = int(matched.group('channel'))
                if cur_measure.measure_number != measure_idx:
                    self.measure_list.append(cur_measure)
                    cur_measure = BMSRawMeasure(measure_idx)
                content = matched.group('content')
                cur_measure.edit_channel(channel, content)
        self.measure_list.append(cur_measure)


class BMSOnsetChart:
    def __init__(self, bms_header: BMSHeader, bms_channels: BMSChannels, bms_audio_obj: MediaObj):
        self.bgm_audio = np.zeros((2, 1))
        self.fs = bms_audio_obj.fs
        cur_bpm = float(bms_header.bpm)
        start_time = 0.0
        self.lane = [[] for i in range(8)]
        for measure in bms_channels.measure_list:
            measure_beats = measure.beats
            bpm_change_onsets = [0.0]
            bpm_list = [cur_bpm]
            bpm_event_idx = 0
            if measure.vary_bpm:
                bpm_change_onsets = [i * measure_beats / len(measure.bpm_channel) for i in range(len(measure.bpm_channel))]
                bpm_list = [cur_bpm] * len(bpm_change_onsets)
                for idx, value in enumerate(measure.bpm_channel):
                    if value != 0:
                        if bms_header.use_bpm_list:
                            cur_bpm = bms_header.bpm_list[int(value, base=36)]
                        else:
                            cur_bpm = int(value, base=16)
                    bpm_list[idx] = cur_bpm
            onset_beat_list = [start_time] * len(bpm_change_onsets)
            for idx in range(1, len(bpm_change_onsets)):
                onset_beat_list[idx] = (bpm_change_onsets[idx] - bpm_change_onsets[idx-1]) * 60 / bpm_list[idx-1]\
                                       + onset_beat_list[idx-1]
            start_time = (measure_beats - bpm_change_onsets[-1]) * 60 / bpm_list[-1] + onset_beat_list[-1]
            for track in measure.bgm:
                onsets = [i * measure_beats / track.size for i in range(track.size)]
                for note_on, note_num in zip(onsets, track):
                    if bpm_event_idx+1 < len(bpm_list):
                        if bpm_change_onsets[bpm_event_idx+1] < note_on:
                            bpm_event_idx += 1
                    act_time = (note_on - bpm_change_onsets[bpm_event_idx]) * 60 / bpm_list[bpm_event_idx]  \
                               + onset_beat_list[bpm_event_idx]
                    act_sample = int(act_time * self.fs)
                    if note_num != 0:
                        audio = bms_audio_obj.media_list[note_num]
                        if self.bgm_audio.shape[-1] < act_sample+audio.shape[-1]:
                            self.bgm_audio = np.concatenate((
                                self.bgm_audio, np.zeros((2, act_sample+audio.shape[-1] - self.bgm_audio.shape[-1]))),
                                axis=1)
                        self.bgm_audio[:, act_sample:act_sample+audio.shape[-1]] += audio
            for idx, visible_lane in enumerate(measure.note_channels):
                onsets = [i * measure_beats / visible_lane.size for i in range(visible_lane.size)]
                for note_on, note_num in zip(onsets, visible_lane):
                    if bpm_event_idx + 1 < len(bpm_list):
                        if bpm_change_onsets[bpm_event_idx + 1] < note_on:
                            bpm_event_idx += 1
                    act_time = (note_on - bpm_change_onsets[bpm_event_idx]) * 60 / bpm_list[bpm_event_idx] \
                               + onset_beat_list[bpm_event_idx]
                    if note_num != 0:
                        self.lane[idx].append(BMSNotes(act_time, note_num))

    def gen_audio(self, bms_audio_obj: MediaObj, save_path):
        out_audio = self.bgm_audio.copy()
        for lane in self.lane:
            for note in lane:
                audio = bms_audio_obj.media_list[note.audio]
                act_sample = int(note.onset * self.fs)
                if out_audio.shape[-1] < act_sample + audio.shape[-1]:
                    out_audio = np.concatenate((
                        out_audio, np.zeros((2, act_sample + audio.shape[-1] - out_audio.shape[-1]))),
                        axis=1)
                out_audio[:, act_sample:act_sample+audio.shape[-1]] += audio
        sf.write(save_path, out_audio.transpose(), self.fs, subtype='FLOAT')


class BMSNotes:
    def __init__(self, onset, audio):
        self.onset = onset
        self.audio = audio


if __name__ == '__main__':
    bms_path = 'ERIS/ERIS[MX].bms'
    data = read_bms_file(bms_path)
    parse_control_flow(data)
    header = BMSHeader(data)
    audio_obj = MediaObj(data, bms_path)
    bms_measures = BMSChannels(data)
    chart = BMSOnsetChart(header, bms_measures, audio_obj)
    chart.gen_audio(audio_obj, 'ERIS.wav')
    print()
