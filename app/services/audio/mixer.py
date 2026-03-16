from pydub import AudioSegment
from pydub.utils import make_chunks
import logging

class PydubMixAudio:

    def init_voice(self, voice_path: str):
        self.voice_file = AudioSegment.from_file(voice_path)

    def add_overlay(self, overlay_path: str, start_time_ms:int, duck_db=-10):
        overlay_file = AudioSegment.from_file(overlay_path)
        overlay_duration = len(overlay_file)

        # 1. 处理主音频 (实现“闪避”效果)
        # 逻辑：将 主音频 切成三段 -> [播报前] + [播报中(降音量)] + [播报后]

        # 计算切分点
        end_time_ms = start_time_ms + overlay_duration

        # 第一段：播报开始前 (保持原音量)
        voice_part_1 = self.voice_file[:start_time_ms]

        # 第二段：播报进行中 (降低音量)
        # 如果播报时间超出了 主音频 长度，切片会自动取到末尾，不会报错
        voice_part_2 = self.voice_file[start_time_ms:end_time_ms]
        voice_part_2_quiet = voice_part_2 + duck_db  # 降低音量

        # 第三段：播报结束后 (保持原音量)
        voice_part_3 = self.voice_file[end_time_ms:]

        # 重新拼接处理后的 主音频
        processed_voice = voice_part_1 + voice_part_2_quiet + voice_part_3

        # 2. 执行叠加 (Overlay)
        # 将原始语音叠加到处理后的 主音频 上
        # position 参数确保语音在正确的时间点响起
        self.voice_file = processed_voice.overlay(overlay_file, position=start_time_ms)

        # 3. 防止爆音 (可选)
        # 如果叠加后总音量过大，可以进行标准化处理 (限制最大峰值)
        # final_audio = normalize(final_audio, headroom=1.0)

    def export(self, output_path: str):
        self.voice_file.export(output_path, format=output_path.split(".")[-1])


if __name__ == "__main__":
    main_mp3 = r"temp/20260225_171806_80dd1add/htdemucs/input/no_vocals.wav"
    insert_wav = r"temp/20260225_171806_80dd1add/htdemucs/input/vocals.wav"
    insert_wav2 = r"zh_female_cancan_mars_bigtts.wav"
    output_mp3 = "merged_result.wav"
    overlayer = PydubMixAudio(voice_path=main_mp3)
    overlayer.add_overlay(insert_wav, 0)
    overlayer.add_overlay(insert_wav2, 5000)
    overlayer.export(output_mp3)
