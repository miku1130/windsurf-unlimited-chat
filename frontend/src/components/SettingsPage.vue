<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useMessage } from 'naive-ui'

interface SoundPreset {
  id: string
  name: string
  filename: string
}

interface AppSettings {
  audio_enabled: boolean
  audio_preset: string
  custom_audio_url: string
  windsurf_configured: boolean
}

const emit = defineEmits<{
  back: []
  themeChange: [theme: string]
}>()

const props = defineProps<{
  currentTheme: string
}>()

// 音频设置
const audioEnabled = ref(true)
const selectedPreset = ref('deng')
const customAudioUrl = ref('')
const useCustomAudio = ref(false)
const isPlaying = ref(false)
const playingId = ref('')

// Windsurf 配置状态
const windsurfConfigured = ref(false)
const configuring = ref(false)
const configResult = ref('')

// 预设音效列表
const presetSounds = ref<SoundPreset[]>([
  { id: '100w', name: '100万', filename: '100w.mp3' },
  { id: 'deng', name: '噔', filename: 'deng.mp3' },
  { id: 'ganma', name: 'iKun', filename: 'ganma.mp3' },
  { id: 'elegant', name: '销魂', filename: 'elegant.mp3' },
  { id: 'gaowan', name: '睾丸了', filename: 'gaowan.mp3' },
  { id: 'dengyixia', name: '等一下', filename: 'dengyixia.mp3' },
  { id: 'ji', name: '鸡', filename: 'ji.mp3' },
])

const currentSoundName = computed(() => {
  if (useCustomAudio.value) return '自定义音效'
  const preset = presetSounds.value.find(s => s.id === selectedPreset.value)
  return preset ? preset.name : '未设置'
})

// 加载设置
async function loadSettings() {
  try {
    const res = await fetch('/api/settings')
    if (res.ok) {
      const settings: AppSettings = await res.json()
      audioEnabled.value = settings.audio_enabled
      selectedPreset.value = settings.audio_preset || 'deng'
      customAudioUrl.value = settings.custom_audio_url || ''
      useCustomAudio.value = !!settings.custom_audio_url
      windsurfConfigured.value = settings.windsurf_configured
    }
  } catch (e) {
    console.error('加载设置失败:', e)
  }
}

// 保存设置
async function saveSettings() {
  try {
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        audio_enabled: audioEnabled.value,
        audio_preset: selectedPreset.value,
        custom_audio_url: useCustomAudio.value ? customAudioUrl.value : '',
      }),
    })
  } catch (e) {
    console.error('保存设置失败:', e)
  }
}

// 选择预设音效
async function selectPreset(presetId: string) {
  selectedPreset.value = presetId
  useCustomAudio.value = false
  await saveSettings()
  await testSound(presetId)
}

// 试听音效
async function testSound(soundId: string) {
  if (isPlaying.value) return
  isPlaying.value = true
  playingId.value = soundId
  try {
    await fetch(`/api/sounds/play/${soundId}`, { method: 'POST' })
  } catch (e) {
    console.error('播放音效失败:', e)
  } finally {
    setTimeout(() => {
      isPlaying.value = false
      playingId.value = ''
    }, 2000)
  }
}

// 切换自定义音效
function selectCustom() {
  useCustomAudio.value = true
}

// 保存自定义音效
async function saveCustomAudio() {
  if (!customAudioUrl.value.trim()) return
  await saveSettings()
}

// 切换音频通知
async function toggleAudio() {
  audioEnabled.value = !audioEnabled.value
  await saveSettings()
}

// 配置 Windsurf 规则
async function configureWindsurf() {
  configuring.value = true
  configResult.value = ''
  try {
    const res = await fetch('/api/configure-windsurf', { method: 'POST' })
    const data = await res.json()
    if (data.success) {
      windsurfConfigured.value = true
      configResult.value = 'success'
    } else {
      configResult.value = data.message || '配置失败'
    }
  } catch (e) {
    configResult.value = '网络错误'
  } finally {
    configuring.value = false
  }
}

onMounted(() => {
  loadSettings()
})

const msg = useMessage()

// 复制文本到剪贴板
function copyText(text: string) {
  navigator.clipboard.writeText(text).then(() => {
    msg.success('已复制: ' + text)
  }).catch(() => {
    msg.error('复制失败')
  })
}
</script>

<template>
  <div class="settings-page" :class="{ dark: currentTheme === 'dark' }">
    <!-- 顶部导航 -->
    <div class="settings-header">
      <button class="back-btn" @click="$emit('back')">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M10 12L6 8L10 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        返回
      </button>
      <h1 class="settings-title">设置</h1>
      <div style="width: 60px"></div>
    </div>

    <div class="settings-content">
      <!-- 音频设置 -->
      <div class="settings-section">
        <div class="section-header">
          <div class="section-icon">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M11 5L6 9H2v6h4l5 4V5z" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              <path d="M19.07 4.93a10 10 0 010 14.14M15.54 8.46a5 5 0 010 7.07" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="section-info">
            <h2>音频设置</h2>
            <p>配置音频通知和提示音</p>
          </div>
        </div>

        <!-- 音频通知开关 -->
        <div class="setting-item">
          <div class="setting-label">
            <span class="dot warning"></span>
            <div>
              <div class="label-text">音频通知</div>
              <div class="label-desc">启用后在MCP工具被触发时播放音频提示</div>
            </div>
          </div>
          <n-switch :value="audioEnabled" size="small" @update:value="toggleAudio" />
        </div>

        <!-- 音效选择 (仅在启用时显示) -->
        <template v-if="audioEnabled">
          <div class="setting-item column">
            <div class="setting-label">
              <span class="dot warning"></span>
              <div class="label-text">音效选择</div>
            </div>

            <!-- 预设音效 -->
            <div class="sound-section">
              <div class="sound-label">预设音效</div>
              <div class="sound-presets">
                <button
                  v-for="preset in presetSounds"
                  :key="preset.id"
                  class="preset-btn"
                  :class="{
                    active: !useCustomAudio && selectedPreset === preset.id,
                    playing: playingId === preset.id
                  }"
                  @click="selectPreset(preset.id)"
                >
                  {{ preset.name }}
                </button>
              </div>
            </div>

            <!-- 自定义音效 -->
            <div class="sound-section">
              <div class="sound-custom-header">
                <div class="sound-label">自定义音效</div>
                <button
                  class="custom-use-btn"
                  :class="{ active: useCustomAudio }"
                  @click="selectCustom"
                >
                  使用自定义
                </button>
              </div>
              <div v-if="useCustomAudio" class="custom-audio-input">
                <n-input
                  v-model:value="customAudioUrl"
                  size="small"
                  placeholder="音效文件路径或URL"
                />
                <n-button
                  type="primary"
                  size="small"
                  :disabled="!customAudioUrl.trim()"
                  @click="saveCustomAudio"
                >
                  保存
                </n-button>
              </div>
            </div>

            <!-- 当前音效 -->
            <div class="current-sound">
              <span class="current-sound-label">当前音效：</span>
              <span class="current-sound-value">{{ currentSoundName }}</span>
            </div>
          </div>
        </template>
      </div>

      <!-- Windsurf 配置 -->
      <div class="settings-section">
        <div class="section-header">
          <div class="section-icon windsurf">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <path d="M12 15V3m0 12l-4-4m4 4l4-4M2 17l.621 2.485A2 2 0 004.561 21h14.878a2 2 0 001.94-1.515L22 17" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </div>
          <div class="section-info">
            <h2>Windsurf 配置</h2>
            <p>自动配置AI提示词规则</p>
          </div>
        </div>

        <div class="setting-item column">
          <div class="windsurf-status">
            <span class="dot" :class="windsurfConfigured ? 'success' : 'default'"></span>
            <span>{{ windsurfConfigured ? '已配置' : '未配置' }}</span>
          </div>
          <p class="windsurf-desc">
            自动向 Windsurf 的 global_rules.md 注入提示词规则，使AI在结束会话前必须调用本工具征求你的反馈。
          </p>
          <n-button
            type="primary"
            size="small"
            :loading="configuring"
            @click="configureWindsurf"
          >
            {{ windsurfConfigured ? '重新配置' : '立即配置' }}
          </n-button>
          <div v-if="configResult === 'success'" class="config-result success">
            配置成功！规则已写入 Windsurf 配置文件。
          </div>
          <div v-else-if="configResult && configResult !== 'success'" class="config-result error">
            {{ configResult }}
          </div>
        </div>
      </div>

      <!-- 关于信息 -->
      <div class="settings-section about-section">
        <div class="section-header">
          <div class="section-icon about">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
              <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
              <line x1="12" y1="16" x2="12" y2="12" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              <line x1="12" y1="8" x2="12.01" y2="8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>
          <div class="section-info">
            <h2>关于</h2>
            <p>软件信息与联系方式</p>
          </div>
        </div>
        <div class="about-content">
          <div class="about-item">
            <span class="about-label">作者</span>
            <span class="about-value">柠檬酱</span>
          </div>
          <div class="about-item">
            <span class="about-label">QQ交流群</span>
            <span class="about-value copyable" @click="copyText('1076144676')">1076144676</span>
          </div>
          <div class="about-item">
            <span class="about-label">软件定制</span>
            <span class="about-value">如需软件定制可联系QQ私聊</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.settings-page {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
  color: #333;
}

.settings-page.dark {
  background: #1a1a1a;
  color: #e0e0e0;
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e8e8e8;
  background: #fff;
  flex-shrink: 0;
}

.dark .settings-header {
  background: #242424;
  border-bottom-color: #3a3a3a;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  border: none;
  background: none;
  color: #52c41a;
  cursor: pointer;
  font-size: 13px;
  border-radius: 4px;
}

.back-btn:hover {
  background: rgba(82, 196, 26, 0.08);
}

.settings-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0;
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
}

.settings-section {
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  margin-bottom: 12px;
}

.dark .settings-section {
  background: #242424;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.dark .section-header {
  border-bottom-color: #3a3a3a;
}

.section-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: #fff7e6;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fa8c16;
  flex-shrink: 0;
}

.dark .section-icon {
  background: #3a2e1a;
}

.section-icon.windsurf {
  background: #e6f7ff;
  color: #1890ff;
}

.dark .section-icon.windsurf {
  background: #1a2e3a;
}

.section-info h2 {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 2px 0;
}

.section-info p {
  font-size: 12px;
  opacity: 0.6;
  margin: 0;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
}

.setting-item.column {
  flex-direction: column;
  align-items: stretch;
  gap: 10px;
}

.setting-label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot.warning { background: #faad14; }
.dot.success { background: #52c41a; }
.dot.default { background: #d9d9d9; }

.label-text {
  font-size: 13px;
  font-weight: 500;
}

.label-desc {
  font-size: 11px;
  opacity: 0.5;
  margin-top: 2px;
}

.sound-section {
  padding-left: 14px;
}

.sound-label {
  font-size: 11px;
  opacity: 0.5;
  margin-bottom: 6px;
}

.sound-presets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.preset-btn {
  padding: 4px 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
  color: #333;
}

.dark .preset-btn {
  background: #333;
  border-color: #555;
  color: #e0e0e0;
}

.preset-btn:hover {
  border-color: #52c41a;
  color: #52c41a;
}

.preset-btn.active {
  background: #52c41a;
  border-color: #52c41a;
  color: #fff;
}

.preset-btn.playing {
  animation: pulse 0.5s ease-in-out;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.sound-custom-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.custom-use-btn {
  padding: 2px 8px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  color: #666;
}

.dark .custom-use-btn {
  background: #333;
  border-color: #555;
  color: #aaa;
}

.custom-use-btn.active {
  background: #52c41a;
  border-color: #52c41a;
  color: #fff;
}

.custom-audio-input {
  display: flex;
  gap: 8px;
}

.current-sound {
  padding: 6px 10px;
  background: #fafafa;
  border-radius: 4px;
  font-size: 11px;
  margin-top: 4px;
  margin-left: 14px;
}

.dark .current-sound {
  background: #1a1a1a;
}

.current-sound-label {
  opacity: 0.5;
}

.current-sound-value {
  font-weight: 500;
}

.windsurf-status {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.windsurf-desc {
  font-size: 12px;
  opacity: 0.6;
  line-height: 1.5;
  margin: 0;
}

.config-result {
  font-size: 12px;
  padding: 6px 10px;
  border-radius: 4px;
  margin-top: 4px;
}

.config-result.success {
  background: #f6ffed;
  color: #52c41a;
  border: 1px solid #b7eb8f;
}

.dark .config-result.success {
  background: #1a2e1a;
  border-color: #3a5a3a;
}

.config-result.error {
  background: #fff2f0;
  color: #ff4d4f;
  border: 1px solid #ffccc7;
}

.dark .config-result.error {
  background: #2e1a1a;
  border-color: #5a3a3a;
}

/* 关于板块 */
.section-icon.about {
  background: #f0f5ff;
  color: #597ef7;
}

.dark .section-icon.about {
  background: #1a2240;
}

.about-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.about-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid #f5f5f5;
}

.about-item:last-child {
  border-bottom: none;
}

.dark .about-item {
  border-bottom-color: #333;
}

.about-label {
  font-size: 12px;
  opacity: 0.5;
  min-width: 70px;
  flex-shrink: 0;
}

.about-value {
  font-size: 13px;
  font-weight: 500;
}

.about-value.copyable {
  color: #52c41a;
  cursor: pointer;
  user-select: all;
}

.about-value.copyable:hover {
  text-decoration: underline;
}
</style>
