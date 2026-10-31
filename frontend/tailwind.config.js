/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts}'],
  theme: {
    extend: {
      colors: {
        paper: '#fbf5ea',
        ink: '#2c2118',
        muted: '#7a6650',
        accent: '#b45309',
      },
      fontFamily: {
        sans: [
          '"HarmonyOS Sans SC"',
          '"PingFang SC"',
          '"Microsoft YaHei"',
          '"Noto Sans SC"',
          'sans-serif',
        ],
      },
    },
  },
  plugins: [],
}
