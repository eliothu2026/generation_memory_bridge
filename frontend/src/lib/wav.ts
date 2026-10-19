/**
 * 把浏览器录音(Chrome 的 webm/opus、Safari 的 m4a)解码并重采样成 16kHz 单声道
 * 16bit PCM WAV。
 *
 * 为什么在前端做:云端 ASR(StepFun / OpenAI 兼容接口)普遍不收 webm,而后端不保证
 * 装了 ffmpeg(本机就没有),所以用 Web Audio API 在浏览器里转一道——本地 whisper
 * 和云端接口都能直接吃 WAV。
 */
export async function toWav16k(blob: Blob): Promise<Blob> {
  const Ctx =
    window.AudioContext ??
    (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
  if (!Ctx) throw new Error('浏览器不支持 Web Audio,无法转码')

  const ctx = new Ctx()
  try {
    const decoded = await ctx.decodeAudioData(await blob.arrayBuffer())
    return encodeWav(resample(downmix(decoded), 16000, decoded.sampleRate), 16000)
  } finally {
    void ctx.close()
  }
}

/** 多声道下混成单声道 */
function downmix(buf: AudioBuffer): Float32Array {
  const channels = buf.numberOfChannels
  const out = new Float32Array(buf.length)
  for (let c = 0; c < channels; c++) {
    const data = buf.getChannelData(c)
    for (let i = 0; i < data.length; i++) out[i] += data[i] / channels
  }
  return out
}

/** 线性插值重采样(语音场景足够,不需要高保真) */
function resample(input: Float32Array, targetRate: number, sourceRate?: number): Float32Array {
  const srcRate = sourceRate ?? 48000
  if (srcRate === targetRate) return input
  const ratio = srcRate / targetRate
  const len = Math.max(1, Math.floor(input.length / ratio))
  const out = new Float32Array(len)
  for (let i = 0; i < len; i++) {
    const pos = i * ratio
    const i0 = Math.floor(pos)
    const i1 = Math.min(i0 + 1, input.length - 1)
    const w = pos - i0
    out[i] = input[i0] * (1 - w) + input[i1] * w
  }
  return out
}

/** Float32 [-1,1] -> 16bit PCM WAV */
function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const buffer = new ArrayBuffer(44 + samples.length * 2)
  const view = new DataView(buffer)
  const writeStr = (offset: number, s: string) => {
    for (let i = 0; i < s.length; i++) view.setUint8(offset + i, s.charCodeAt(i))
  }

  writeStr(0, 'RIFF')
  view.setUint32(4, 36 + samples.length * 2, true)
  writeStr(8, 'WAVE')
  writeStr(12, 'fmt ')
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate
  view.setUint16(32, 2, true) // block align
  view.setUint16(34, 16, true) // bits per sample
  writeStr(36, 'data')
  view.setUint32(40, samples.length * 2, true)

  let offset = 44
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]))
    view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7fff, true)
    offset += 2
  }
  return new Blob([view], { type: 'audio/wav' })
}
