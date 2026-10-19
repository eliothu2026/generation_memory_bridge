/** @type {import('tailwindcss').Config} */
// Forest 设计系统:与静态演示 demo(记忆桥_纯前端演示demo_web端.html)同源。
// 所有颜色经 CSS 变量间接定义(见 src/index.css),暗色模式随
// prefers-color-scheme 自动翻转,无需在组件里写 dark: 变体。
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'media',
  theme: {
    extend: {
      fontFamily: {
        sans: [
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'PingFang SC',
          'Hiragino Sans GB',
          'Microsoft YaHei',
          'system-ui',
          'sans-serif',
        ],
      },
      colors: {
        surface: 'rgb(var(--surface) / <alpha-value>)', // 次级面(近白暖纸)
        elev: 'rgb(var(--elev) / <alpha-value>)', // 浮起元素(输入框/按钮,暗色下为深色)
        canvas: 'rgb(var(--canvas) / <alpha-value>)', // 对话区底色(暖纸)
        sidebar: 'rgb(var(--card-left) / <alpha-value>)', // 左栏 = demo 左卡(纯白)
        card: 'rgb(var(--card) / <alpha-value>)', // 右卡(柔和米白)
        ink: 'rgb(var(--ink) / <alpha-value>)',
        subtle: 'rgb(var(--muted) / <alpha-value>)',
        faint: 'rgb(var(--faint) / <alpha-value>)',
        accent: 'rgb(var(--accent) / <alpha-value>)', // 森林绿(文字/图标)
        'accent-fill': 'rgb(var(--accent-fill) / <alpha-value>)', // 实心按钮/实心气泡
        'accent-strong': 'rgb(var(--accent-strong) / <alpha-value>)',
        'on-accent': 'rgb(var(--on-accent) / <alpha-value>)',
        danger: 'rgb(var(--danger) / <alpha-value>)',
        elder: 'rgb(var(--elder) / <alpha-value>)', // 老人气泡底色
        scroll: 'rgb(var(--scroll) / <alpha-value>)',
        line: 'rgb(var(--line) / var(--line-a))', // 分隔线(透明度经变量,暗色下为白)
      },
      boxShadow: {
        soft: 'var(--shadow-sm)',
        panel: 'var(--shadow-float)',
        float: 'var(--shadow-float)',
      },
      borderRadius: {
        bubble: '18px', // 聊天气泡
        card: '14px', // 卡片
        panel: '22px', // 大面板
      },
      keyframes: {
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in': {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        // 「识别和理解中」三点跳动(与 demo 的 tdot 一致)
        dot: {
          '0%, 100%': { opacity: '0.3', transform: 'translateY(0)' },
          '50%': { opacity: '1', transform: 'translateY(-3px)' },
        },
        // 聆听态声波(与 demo 的 wave 一致)
        wave: {
          '0%, 100%': { height: '5px', opacity: '0.5' },
          '50%': { height: '17px', opacity: '1' },
        },
      },
      animation: {
        'fade-in-up': 'fade-in-up 0.35s cubic-bezier(0.2, 0, 0, 1) both',
        'fade-in': 'fade-in 0.3s ease-out both',
        dot: 'dot 1s ease-in-out infinite',
        wave: 'wave 1.1s ease-in-out infinite',
      },
    },
  },
  plugins: [],
}
