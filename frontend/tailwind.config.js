export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Noto Sans", "Noto Sans Tamil", "system-ui", "sans-serif"]
      },
      boxShadow: {
        glass: "0 24px 70px rgba(15, 23, 42, 0.14)"
      }
    }
  },
  plugins: []
};
