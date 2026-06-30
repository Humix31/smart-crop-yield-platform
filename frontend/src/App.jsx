import React, { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Bar, Line } from "react-chartjs-2";
import { FiActivity, FiCloudRain, FiDroplet, FiGlobe, FiLogIn, FiMapPin, FiMoon, FiRefreshCw, FiShield, FiSliders, FiSun, FiThermometer, FiUserPlus, FiWifi } from "react-icons/fi";

import { getDistrictLabel } from "./districtLabels.js";
import { districts, getTalukLabel, getTaluks, getVillages, locationDataSource, officialLocationDataAvailable, officialTalukDataAvailable } from "./data/tamilNaduLocations.js";
import { getCurrentUser, getPredictionHistory, getSensorCalibration, getSensorData, getUsers, getWeather, loginUser, predictYield, registerUser, saveSensorCalibration } from "./services/api";

const crops = ["Paddy", "Tomato", "Sugarcane", "Maize", "Cotton", "Groundnut", "Banana", "Millet", "Chilli", "Coconut"];
const seasons = ["Kharif", "Rabi", "Summer", "Whole Year"];
const languageOptions = [
  { code: "en", label: "English" },
  { code: "ta", label: "Tamil" },
  { code: "hi", label: "Hindi" },
  { code: "ml", label: "Malayalam" },
  { code: "te", label: "Telugu" },
  { code: "kn", label: "Kannada" }
];

const initialDistrict = districts[0] || "Ariyalur";
const initialTaluk = getTaluks(initialDistrict)[0] || "";

const initialForm = {
  district: initialDistrict,
  taluk: initialTaluk,
  village: "",
  crop: "Tomato",
  season: "Kharif",
  area: 2,
  actual_rainfall: 0,
  normal_rainfall: 760,
  deviation: 0
};

const initialLogin = { email: "", password: "", role: "farmer" };
const initialRegister = { name: "", email: "", phone: "", password: "", role: "farmer", district: initialDistrict, taluk: initialTaluk, language: "en" };
const tempUnit = `${String.fromCharCode(176)}C`;

function Card({ children, className = "" }) {
  return <section className={`panel ${className}`}>{children}</section>;
}

function SectionTitle({ eyebrow, title, helper }) {
  return (
    <div className="section-title">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h2>{title}</h2>
      {helper && <p>{helper}</p>}
    </div>
  );
}

function StepTitle({ number, title, helper }) {
  return (
    <div className="mb-4 flex gap-3">
      <span className="step-badge">{number}</span>
      <div>
        <h3 className="text-lg font-bold">{title}</h3>
        <p className="text-sm leading-6 text-stone-600 dark:text-stone-300">{helper}</p>
      </div>
    </div>
  );
}

function Stat({ icon: Icon, label, value, tone = "leaf" }) {
  return (
    <div className={`stat-tile tone-${tone}`}>
      <span className="stat-icon"><Icon size={21} /></span>
      <div>
        <p className="text-xs font-semibold uppercase text-stone-500 dark:text-stone-400">{label}</p>
        <p className="text-xl font-bold text-stone-950 dark:text-white">{value}</p>
      </div>
    </div>
  );
}

export default function App() {
  const { t, i18n } = useTranslation();
  const [dark, setDark] = useState(() => localStorage.getItem("smartCropTheme") === "dark");
  const [form, setForm] = useState(initialForm);
  const [weather, setWeather] = useState(null);
  const [weatherLoading, setWeatherLoading] = useState(false);
  const [weatherMessage, setWeatherMessage] = useState("");
  const [latestSensor, setLatestSensor] = useState(null);
  const [history, setHistory] = useState([]);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const [statusMessage, setStatusMessage] = useState("");
  const [authMode, setAuthMode] = useState("login");
  const [loginForm, setLoginForm] = useState(initialLogin);
  const [registerForm, setRegisterForm] = useState(initialRegister);
  const [authMessage, setAuthMessage] = useState("");
  const [registeredUsers, setRegisteredUsers] = useState([]);
  const [calibration, setCalibration] = useState({ dry_value: 3500, wet_value: 1200, pump_on_below: 35, pump_off_above: 65 });
  const [calibrationMessage, setCalibrationMessage] = useState("");
  const [session, setSession] = useState(() => {
    try {
      const token = localStorage.getItem("smartCropToken");
      const stored = JSON.parse(localStorage.getItem("smartCropUser") || "null");
      return token && stored?.email ? { ...stored, token } : null;
    } catch { return null; }
  });
  const currentLanguage = i18n.resolvedLanguage || i18n.language;

  const taluks = useMemo(() => getTaluks(form.district), [form.district]);
  const villages = useMemo(() => getVillages(form.district, form.taluk), [form.district, form.taluk]);
  const selectedDistrictName = getDistrictLabel(form.district, currentLanguage);
  const officialVillageDatasetMessage = t("officialVillageDatasetMissing");
  const villageSelectionAvailable = officialLocationDataAvailable && villages.length > 0;
  const locationReady = Boolean(form.district);
  const canPredict = Boolean(session && locationReady && form.crop && form.season && Number(form.area) > 0);
  const hasSensorData = Boolean(latestSensor);
  const selectedTalukName = getTalukLabel(form.district, form.taluk);
  const locationLine = [selectedDistrictName, selectedTalukName, form.village].filter(Boolean).join(" / ") || selectedDistrictName;
  const weatherCondition = weather?.condition || weather?.forecast?.[0]?.summary || t("notFetched");
  const pumpOn = String(latestSensor?.pump_status || "OFF").toUpperCase() === "ON";
  const esp32Online = String(latestSensor?.esp32_status || "offline").toLowerCase() === "online";
  const mapQuery = encodeURIComponent(`${form.village || selectedTalukName || form.district}, ${form.district}, Tamil Nadu, India`);
  const soilRawValue = latestSensor?.soil_raw ?? "-";
  const calibratedSoilMoisture = latestSensor?.soil_raw == null ? latestSensor?.soil_moisture : Math.max(0, Math.min(100, ((Number(latestSensor.soil_raw) - Number(calibration.dry_value)) / (Number(calibration.wet_value) - Number(calibration.dry_value))) * 100));

  useEffect(() => {
    document.documentElement.classList.toggle("dark", dark);
    document.body.classList.toggle("dark", dark);
    localStorage.setItem("smartCropTheme", dark ? "dark" : "light");
  }, [dark]);

  useEffect(() => {
    const loadLive = () => {
      getSensorData().then((data) => setLatestSensor(data || null)).catch(() => setLatestSensor(null));
      if (session) {
        getPredictionHistory().then(setHistory).catch(() => setHistory([]));
        getUsers().then(setRegisteredUsers).catch(() => setRegisteredUsers([]));
      } else {
        setHistory([]);
        setRegisteredUsers([]);
      }
      getSensorCalibration().then(setCalibration).catch(() => {});
    };
    loadLive();
    const timer = window.setInterval(loadLive, 5000);
    return () => window.clearInterval(timer);
  }, [session]);

  const yieldData = useMemo(() => {
    const rows = history.slice(0, 8).reverse();
    return { labels: rows.map((row) => t(`crops.${row.crop}`, row.crop)), datasets: [{ label: t("predictedYield"), data: rows.map((row) => row.prediction), borderColor: "#2f6f3e", backgroundColor: "rgba(47,111,62,0.18)", fill: true, tension: 0.35 }] };
  }, [history, t]);
  const rainfallData = { labels: [t("months.jan"), t("months.feb"), t("months.mar"), t("months.apr"), t("months.may"), t("months.jun")], datasets: [{ label: t("rainfall"), data: [34, 42, 51, 88, 120, Number(form.actual_rainfall || 0) / 8], backgroundColor: "#4f8f46" }] };

  function clearPredictionState() {
    setResult(null);
    setStatusMessage("");
  }

  function updateForm(patch) {
    setForm((current) => ({ ...current, ...patch }));
    clearPredictionState();
  }

  function clearUserState() {
    setForm(initialForm);
    setWeather(null);
    setWeatherMessage("");
    setHistory([]);
    setResult(null);
    setStatusMessage("");
    setAuthMessage("");
    setLoginForm(initialLogin);
    setRegisterForm({ ...initialRegister, district: initialDistrict, taluk: initialTaluk });
  }

  function scrollToSection(id) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function openWeatherSection() {
    scrollToSection("weather");
    if (form.district && !weatherLoading) handleWeather(form.district);
  }

  function resetWeather(nextForm) {
    setForm(nextForm);
    setWeather(null);
    clearPredictionState();
    setWeatherMessage(t("weatherAfterLocation"));
  }

  function updateDistrict(district) {
    const nextTaluk = getTaluks(district)[0] || "";
    const nextVillage = getVillages(district, nextTaluk)[0] || "";
    resetWeather({ ...form, district, taluk: nextTaluk, village: nextVillage });
  }

  function updateTaluk(taluk) {
    const nextVillage = getVillages(form.district, taluk)[0] || "";
    resetWeather({ ...form, taluk, village: nextVillage });
  }

  async function handleWeather(districtName = form.district) {
    if (!districtName) {
      setWeatherMessage(t("selectFullLocation"));
      return null;
    }
    setWeatherLoading(true);
    setWeatherMessage(t("fetchingWeather"));
    try {
      const data = await getWeather(districtName);
      setWeather(data);
      setForm((current) => ({ ...current, actual_rainfall: Number(data?.rainfall || 0) }));
      setResult(null);
      setWeatherMessage(data?.message || (data?.source === "demo" ? t("demoWeatherNote") : t("liveWeatherUpdated")));
      return data;
    } catch (error) {
      setWeather(null);
      setWeatherMessage(error?.response?.data?.detail || t("weatherFailed"));
      return null;
    } finally {
      setWeatherLoading(false);
    }
  }

  useEffect(() => {
    if (form.district) handleWeather(form.district);
  }, [form.district]);

  async function handlePrediction(event) {
    event.preventDefault();
    if (!session) {
      setStatusMessage(t("loginRequired"));
      return;
    }
    if (!canPredict) {
      setStatusMessage(t("predictionFormIncomplete"));
      return;
    }
    setLoading(true);
    setResult(null);
    setStatusMessage("");
    try {
      const activeWeather = weather || await handleWeather(form.district);
      const payload = {
        district: form.district,
        taluk: selectedTalukName || form.taluk || null,
        village: villageSelectionAvailable ? form.village : null,
        crop: form.crop,
        season: form.season,
        area: Number(form.area),
        actual_rainfall: Number(activeWeather?.rainfall ?? form.actual_rainfall ?? 0),
        normal_rainfall: Number(form.normal_rainfall),
        deviation: Number(form.deviation)
      };
      const data = await predictYield(payload);
      setResult(data);
      setStatusMessage(t("predictionReady", { district: selectedDistrictName, status: data.model_status }));

      getPredictionHistory().then(setHistory).catch(() => {});
    } catch (error) {
      setStatusMessage(error?.response?.data?.detail || t("predictionFailed"));
    } finally {
      setLoading(false);
    }
  }

  async function handleAuth(event) {
    event.preventDefault();
    const isRegister = authMode === "register";
    const activeForm = isRegister ? registerForm : loginForm;
    const missing = [];
    if (isRegister && !activeForm.name.trim()) missing.push(t("nameRequired"));
    if (!activeForm.email.trim()) missing.push(t("emailRequired"));
    if (!activeForm.password.trim()) missing.push(t("passwordRequired"));
    if (!activeForm.role) missing.push(t("roleRequired"));
    if (missing.length) {
      setAuthMessage(missing.join(" "));
      return;
    }
    setAuthMessage(t("authWorking"));
    try {
      if (isRegister) {
        await registerUser({
          name: activeForm.name.trim(),
          email: activeForm.email.trim(),
          phone: activeForm.phone || null,
          password: activeForm.password,
          role: activeForm.role,
          district: activeForm.district || null,
          taluk: activeForm.taluk ? getTalukLabel(activeForm.district, activeForm.taluk) : null,
          language: i18n.language || "en"
        });
        localStorage.removeItem("smartCropToken");
        localStorage.removeItem("smartCropUser");
        localStorage.removeItem("smartCropSession");
        setSession(null);
        setRegisterForm({ ...initialRegister, district: initialDistrict, taluk: initialTaluk });
        setLoginForm({ email: activeForm.email.trim(), password: "", role: activeForm.role });
        setAuthMode("login");
        clearUserState();
        setLoginForm({ email: activeForm.email.trim(), password: "", role: activeForm.role });
        setAuthMessage("Registration successful. Please login with your email and password.");
        return;
      }

      localStorage.removeItem("smartCropToken");
      localStorage.removeItem("smartCropUser");
      localStorage.removeItem("smartCropSession");
      const data = await loginUser({ email: activeForm.email.trim(), password: activeForm.password, role: activeForm.role });
      localStorage.setItem("smartCropToken", data.access_token);
      const currentUser = await getCurrentUser().catch(() => data);
      const nextSession = {
        token: data.access_token,
        id: currentUser.id || data.id,
        email: currentUser.email || data.email || activeForm.email.trim(),
        role: currentUser.role || data.role,
        name: currentUser.name || data.name,
        district: currentUser.district || data.district || null,
        taluk: currentUser.taluk || data.taluk || null
      };
      localStorage.setItem("smartCropUser", JSON.stringify(nextSession));
      setSession(nextSession);
      setResult(null);
      setStatusMessage("");
      setHistory([]);
      setAuthMessage(t("authSuccess", { name: nextSession.name, role: nextSession.role }));
      getPredictionHistory().then(setHistory).catch(() => setHistory([]));
      getUsers().then(setRegisteredUsers).catch(() => {});
    } catch (error) {
      setAuthMessage(error?.response?.data?.detail || t("authFailed"));
    }
  }

  function logout() {
    localStorage.removeItem("smartCropToken");
    localStorage.removeItem("smartCropUser");
    localStorage.removeItem("smartCropSession");
    setSession(null);
    clearUserState();
    setRegisteredUsers([]);
    setAuthMessage(t("loggedOut"));
  }

  function setCurrentRawAs(type) {
    if (latestSensor?.soil_raw == null) {
      setCalibrationMessage(t("noRawSoilValue"));
      return;
    }
    setCalibration((current) => ({ ...current, [type]: Number(latestSensor.soil_raw) }));
    setCalibrationMessage(type === "dry_value" ? t("dryValueSelected") : t("wetValueSelected"));
  }

  async function handleSaveCalibration() {
    try {
      const payload = {
        dry_value: Number(calibration.dry_value),
        wet_value: Number(calibration.wet_value),
        pump_on_below: Number(calibration.pump_on_below),
        pump_off_above: Number(calibration.pump_off_above)
      };
      const data = await saveSensorCalibration(payload);
      setCalibration(data);
      setCalibrationMessage(t("calibrationSaved"));
    } catch (error) {
      setCalibrationMessage(error?.response?.data?.detail || t("calibrationFailed"));
    }
  }
  const authPanel = (
    <Card id="login" className="w-full max-w-xl">
      <SectionTitle eyebrow={t("secureAccess")} title={t("login")} helper={t("loginGateHelper")} />
      <form className="mt-4 space-y-3" onSubmit={handleAuth}>
        <div className="grid grid-cols-2 gap-2">
          <button type="button" className={authMode === "login" ? "tab-active" : "tab-button"} onClick={() => setAuthMode("login")}><FiLogIn /> {t("login")}</button>
          <button type="button" className={authMode === "register" ? "tab-active" : "tab-button"} onClick={() => setAuthMode("register")}><FiUserPlus /> {t("register")}</button>
        </div>
        {authMode === "register" && <>
          <input className="field" required placeholder={t("name")} value={registerForm.name} onChange={(e) => setRegisterForm({ ...registerForm, name: e.target.value })} />
          <input className="field" placeholder={t("phone")} value={registerForm.phone} onChange={(e) => setRegisterForm({ ...registerForm, phone: e.target.value })} />
          <select className="field" required value={registerForm.role} onChange={(e) => setRegisterForm({ ...registerForm, role: e.target.value })}>
            <option value="farmer">{t("farmer")}</option>
            <option value="officer">{t("agricultureOfficer")}</option>
            <option value="admin">{t("admin")}</option>
          </select>
          <select className="field" value={registerForm.district} onChange={(e) => { const district = e.target.value; const taluk = getTaluks(district)[0] || ""; setRegisterForm({ ...registerForm, district, taluk }); }}>
            {districts.map((item) => <option key={item} value={item}>{getDistrictLabel(item, currentLanguage)}</option>)}
          </select>
          <select className="field" value={registerForm.taluk} onChange={(e) => setRegisterForm({ ...registerForm, taluk: e.target.value })}>
            {getTaluks(registerForm.district).map((item) => <option key={item} value={item}>{getTalukLabel(registerForm.district, item)}</option>)}
          </select>
        </>}
        <input className="field" required type="email" placeholder={t("email")} value={authMode === "login" ? loginForm.email : registerForm.email} onChange={(e) => authMode === "login" ? setLoginForm({ ...loginForm, email: e.target.value }) : setRegisterForm({ ...registerForm, email: e.target.value })} />
        <input className="field" required type="password" minLength={6} placeholder={t("password")} value={authMode === "login" ? loginForm.password : registerForm.password} onChange={(e) => authMode === "login" ? setLoginForm({ ...loginForm, password: e.target.value }) : setRegisterForm({ ...registerForm, password: e.target.value })} />
        {authMode === "login" && <select className="field" required value={loginForm.role} onChange={(e) => setLoginForm({ ...loginForm, role: e.target.value })}>
          <option value="farmer">{t("farmer")}</option>
          <option value="officer">{t("agricultureOfficer")}</option>
          <option value="admin">{t("admin")}</option>
        </select>}
        <button className="btn-primary w-full">{authMode === "login" ? t("login") : t("register")}</button>
        {authMessage && <p className="notice info">{authMessage}</p>}
      </form>
    </Card>
  );

  if (!session) {
    return (
      <main className="app-shell min-h-screen text-stone-950 transition dark:text-stone-100">
        <nav className="nav-shell">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
            <div className="flex items-center gap-3"><span className="brand-mark"><FiActivity /></span><span className="text-base font-extrabold">{t("appName")}</span></div>
            <div className="flex items-center gap-2"><FiGlobe className="text-stone-500" /><select className="field min-w-[132px]" value={i18n.language} onChange={(event) => i18n.changeLanguage(event.target.value)} aria-label={t("language")}>{languageOptions.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select><button className="icon-button" title={dark ? t("lightMode") : t("darkMode")} onClick={() => setDark((value) => !value)}>{dark ? <FiSun /> : <FiMoon />}</button></div>
          </div>
        </nav>
        <section className="mx-auto flex min-h-[calc(100vh-76px)] max-w-7xl items-center justify-center px-4 py-10">
          {authPanel}
        </section>
      </main>
    );
  }

  return (
    <main className="app-shell min-h-screen text-stone-950 transition dark:text-stone-100">
      <nav className="nav-shell">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3">
          <div className="flex items-center gap-3"><span className="brand-mark"><FiActivity /></span><span className="text-base font-extrabold">{t("appName")}</span></div>
          <div className="hidden items-center gap-2 text-sm font-semibold text-stone-600 dark:text-stone-300 md:flex">{session && <><button type="button" className="nav-action" onClick={() => scrollToSection("dashboard")}>{t("dashboard")}</button><button type="button" className="nav-action" onClick={() => scrollToSection("predict")}>{t("predictYield")}</button><button type="button" className="nav-action" onClick={openWeatherSection}>{t("weather")}</button><button type="button" className="nav-action danger" onClick={logout}>{t("logout")}</button></>}</div>
          <div className="flex items-center gap-2"><FiGlobe className="text-stone-500" /><select className="field min-w-[132px]" value={i18n.language} onChange={(event) => i18n.changeLanguage(event.target.value)} aria-label={t("language")}>{languageOptions.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}</select><button className="icon-button" title={dark ? t("lightMode") : t("darkMode")} onClick={() => setDark((value) => !value)}>{dark ? <FiSun /> : <FiMoon />}</button></div>
        </div>
      </nav>

      <header className="hero-shell">
        <div className="hero-image" />
        <div className="hero-overlay" />
        <div className="relative mx-auto grid max-w-7xl gap-6 px-4 py-10 md:grid-cols-[1.08fr_0.92fr] md:py-14">
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }} className="max-w-3xl text-white">
            <p className="hero-badge">{t("dashboardBadge")}</p>
            <h1 className="text-4xl font-extrabold leading-tight md:text-5xl">{t("heroTitle")}</h1>
            <p className="mt-5 max-w-2xl text-base leading-8 text-emerald-50 md:text-lg">{t("heroSubtitle")}</p>
            <div className="field-strip mt-7">
              <span><FiShield /> {t("signedInFarmer", { name: session.name })}</span>
              <span><FiCloudRain /> {weather?.source === "openweathermap" ? t("liveWeatherUpdated") : t("weatherAfterLocation")}</span>
              <span><FiMapPin /> {t("officialVillageDataLoaded")}</span>
            </div>
            <div className="mt-8 flex flex-wrap gap-3"><a className="btn-primary bg-white text-green-900 hover:bg-green-50" href="#predict">{t("startPrediction")}</a></div>
          </motion.div>
          <Card className="self-end">
            <p className="eyebrow">{t("farmerTrustCard")}</p>
            <p className="mt-3 text-2xl font-extrabold text-green-900 dark:text-green-100">{locationLine}</p>
            <p className="mt-3 text-sm leading-6 text-stone-600 dark:text-stone-300">{weatherLoading ? t("fetchingWeather") : weatherMessage || t("weatherAfterLocation")}</p>
            {!officialLocationDataAvailable && <p className="notice warn mt-4">{officialVillageDatasetMessage}</p>}
          </Card>
        </div>
      </header>

      <div id="dashboard" className="dashboard-grid mx-auto grid max-w-7xl gap-5 px-4 py-8 lg:grid-cols-[1.05fr_0.95fr]">
        <form id="predict" onSubmit={handlePrediction} className="space-y-5">
          <Card>
            <StepTitle number="1" title={t("stepLocation")} helper={t("locationHelper")} />
            <div className="grid gap-4 md:grid-cols-3">
              <label className="text-sm font-semibold">{t("district")}<select className="field mt-1" value={form.district} onChange={(e) => updateDistrict(e.target.value)}>{districts.map((item) => <option key={item} value={item}>{getDistrictLabel(item, currentLanguage)}</option>)}</select><span className="helper-text">{t("selectDistrict")}</span></label>
              <label className="text-sm font-semibold">{t("taluk")}<select className="field mt-1" value={form.taluk} disabled={!officialTalukDataAvailable || taluks.length === 0} onChange={(e) => updateTaluk(e.target.value)}><option value="">{t("officialDataNeeded")}</option>{taluks.map((item) => <option key={item} value={item}>{getTalukLabel(form.district, item)}</option>)}</select><span className="helper-text">{t("selectTaluk")}</span></label>
              {villageSelectionAvailable ? <label className="text-sm font-semibold">{t("village")}<select className="field mt-1" value={form.village} onChange={(e) => updateForm({ village: e.target.value })}><option value="">{t("selectVillage")}</option>{villages.map((item) => <option key={item} value={item}>{item}</option>)}</select><span className="helper-text">{t("selectVillage")}</span></label> : <div className="notice info md:col-span-1">{officialVillageDatasetMessage}</div>}
            </div>
            <p className="notice warn mt-4"><FiShield /> {officialLocationDataAvailable ? (locationDataSource.message || locationDataSource.note) : officialVillageDatasetMessage}</p>
          </Card>

          <Card>
            <StepTitle number="2" title={t("stepCrop")} helper={t("cropHelper")} />
            <div className="grid gap-4 md:grid-cols-3">
              <label className="text-sm font-semibold">{t("crop")}<select className="field mt-1" value={form.crop} onChange={(e) => updateForm({ crop: e.target.value })}>{crops.map((item) => <option key={item} value={item}>{t(`crops.${item}`, item)}</option>)}</select></label>
              <label className="text-sm font-semibold">{t("season")}<select className="field mt-1" value={form.season} onChange={(e) => updateForm({ season: e.target.value })}>{seasons.map((item) => <option key={item} value={item}>{t(`seasons.${item}`, item)}</option>)}</select></label>
              <label className="text-sm font-semibold">{t("area")}<input className="field mt-1" type="number" min="0.1" step="0.1" value={form.area} onChange={(e) => updateForm({ area: Number(e.target.value) })} /></label>
            </div>
          </Card>

          <Card id="weather">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><StepTitle number="3" title={t("stepWeather")} helper={t("weatherHelper")} /><button type="button" className="btn-secondary" onClick={() => handleWeather(form.district)} disabled={weatherLoading}>{weatherLoading ? t("fetchingWeather") : "Refresh weather"}</button></div>

            {weatherLoading && <p className="notice info mt-3"><FiRefreshCw className="animate-spin" /> {t("fetchingWeather")}</p>}
            {weatherMessage && !weatherLoading && <p className={weather?.source === "demo" ? "notice warn mt-3" : "notice success mt-3"}>{weatherMessage}</p>}
            {weather && <div className="mt-4 grid gap-3 sm:grid-cols-2"><Stat icon={FiThermometer} label={t("temperature")} value={`${weather.temperature}${tempUnit}`} tone="heat" /><Stat icon={FiDroplet} label={t("humidity")} value={`${weather.humidity}%`} tone="water" /><Stat icon={FiCloudRain} label={t("rainfall")} value={`${weather.rainfall} mm`} /><Stat icon={FiRefreshCw} label={t("wind")} value={`${weather.wind} km/h`} tone="soil" /><Stat icon={FiCloudRain} label={t("weatherCondition")} value={weatherCondition} tone="neutral" /><Stat icon={FiActivity} label={t("weatherAlert")} value={weather.alert || (Number(weather.rainfall) > 20 ? t("heavyRainAlert") : t("normalWeatherAlert"))} tone="leaf" /></div>}
            {weather && <div className="mt-4 grid gap-4 md:grid-cols-3"><label className="text-sm font-semibold">{t("actualRainfall")}<input className="field mt-1" type="number" value={form.actual_rainfall} onChange={(e) => updateForm({ actual_rainfall: Number(e.target.value) })} /></label><label className="text-sm font-semibold">{t("normalRainfall")}<input className="field mt-1" type="number" value={form.normal_rainfall} onChange={(e) => updateForm({ normal_rainfall: Number(e.target.value) })} /></label><label className="text-sm font-semibold">{t("deviation")}<input className="field mt-1" type="number" value={form.deviation} onChange={(e) => updateForm({ deviation: Number(e.target.value) })} /></label></div>}
          </Card>

          <Card>
            <StepTitle number="4" title={t("stepPrediction")} helper={t("predictionHelper")} />

            {statusMessage && <p className="notice info mb-3">{statusMessage}</p>}
            <button className="btn-primary" disabled={loading || !session} aria-busy={loading}>{loading ? t("predicting") : t("getPrediction")}</button>
          </Card>
        </form>

        <div className="space-y-5">
          <Card><SectionTitle title={t("predictedYield")} helper={t("predictionPlaceholder")} />{result && <div className="mt-4"><div className="space-y-1 text-sm font-semibold text-stone-600 dark:text-stone-300"><p>District: {result.location?.district || form.district || "-"}</p><p>Taluk: {result.location?.taluk || selectedTalukName || "-"}</p><p>Village: {result.location?.village || form.village || (officialLocationDataAvailable ? "-" : officialVillageDatasetMessage)}</p></div><div className="mt-3 flex items-end gap-2"><span className="text-5xl font-extrabold text-green-800 dark:text-green-200">{result.predicted_yield}</span><span className="mb-2 text-sm text-stone-500">{result.unit}</span></div><p className="notice success mt-4">{t("districtLevelNote")}</p><div className="mt-5 space-y-3 text-sm leading-6"><p><strong>{t("fertilizer")}:</strong> {result.recommendation.fertilizer}</p><p><strong>{t("irrigation")}:</strong> {result.recommendation.irrigation}</p><p><strong>{t("sowingPeriod")}:</strong> {result.recommendation.sowing_period}</p><p><strong>{t("harvestPeriod")}:</strong> {result.recommendation.harvest_period}</p><p><strong>{t("alert")}:</strong> {result.recommendation.alert}</p></div></div>}</Card>
          <Card><SectionTitle title={t("sensorValues")} helper={t("sensorHelper")} />{!hasSensorData ? <p className="notice info mt-4">{t("noSensorData")}</p> : <div className="mt-4 grid gap-3 sm:grid-cols-2"><Stat icon={FiThermometer} label={t("temperature")} value={`${latestSensor.temperature}${tempUnit}`} tone="heat" /><Stat icon={FiDroplet} label={t("humidity")} value={`${latestSensor.humidity}%`} tone="water" /><Stat icon={FiActivity} label={t("soilRaw")} value={soilRawValue} tone="soil" /><Stat icon={FiActivity} label={t("soilMoisture")} value={`${Math.round(calibratedSoilMoisture ?? latestSensor.soil_moisture)}%`} /><Stat icon={FiRefreshCw} label={t("pumpStatus")} value={pumpOn ? t("pumpOn") : t("pumpOff")} tone={pumpOn ? "leaf" : "danger"} /><Stat icon={FiWifi} label={t("esp32Status")} value={esp32Online ? t("esp32Online") : t("esp32Offline")} tone={esp32Online ? "leaf" : "danger"} /></div>}</Card>
          
          <Card><SectionTitle title={t("iotCalibration")} helper={t("iotCalibrationHelper")} />
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <Stat icon={FiSliders} label={t("currentRawSoil")} value={soilRawValue} tone="soil" />
              <Stat icon={FiActivity} label={t("calculatedMoisture")} value={hasSensorData ? `${Math.round(calibratedSoilMoisture ?? latestSensor.soil_moisture)}%` : "-"} tone="leaf" />
            </div>
            <div className="mt-4 grid gap-3 sm:grid-cols-2">
              <button type="button" className="btn-secondary" onClick={() => setCurrentRawAs("dry_value")}>{t("setCurrentDry")}</button>
              <button type="button" className="btn-secondary" onClick={() => setCurrentRawAs("wet_value")}>{t("setCurrentWet")}</button>
              <label className="text-sm font-semibold">{t("dryValue")}<input className="field mt-1" type="number" value={calibration.dry_value} onChange={(e) => setCalibration({ ...calibration, dry_value: Number(e.target.value) })} /></label>
              <label className="text-sm font-semibold">{t("wetValue")}<input className="field mt-1" type="number" value={calibration.wet_value} onChange={(e) => setCalibration({ ...calibration, wet_value: Number(e.target.value) })} /></label>
              <label className="text-sm font-semibold">{t("pumpOnBelow")}<input className="field mt-1" type="number" min="0" max="100" value={calibration.pump_on_below} onChange={(e) => setCalibration({ ...calibration, pump_on_below: Number(e.target.value) })} /></label>
              <label className="text-sm font-semibold">{t("pumpOffAbove")}<input className="field mt-1" type="number" min="0" max="100" value={calibration.pump_off_above} onChange={(e) => setCalibration({ ...calibration, pump_off_above: Number(e.target.value) })} /></label>
            </div>
            <button type="button" className="btn-primary mt-4" onClick={handleSaveCalibration}>{t("saveCalibration")}</button>
            {calibrationMessage && <p className="notice info mt-3">{calibrationMessage}</p>}
            <p className="helper-text mt-3">{t("calibrationSteps")}</p>
          </Card>
          <Card><SectionTitle title={t("map")} helper={t("mapFor", { district: selectedDistrictName })} /><iframe title="district-map" className="mt-4 h-72 w-full rounded-lg border-0" loading="lazy" src={`https://www.google.com/maps?q=${mapQuery}&output=embed`} /></Card>
        </div>

        <Card><SectionTitle title={t("cropYieldTrends")} helper="This chart uses only your saved predictions." />{history.length ? <Line data={yieldData} options={{ responsive: true, plugins: { legend: { display: false } } }} /> : <p className="notice info mt-4">No prediction history yet for this account.</p>}</Card>
        <Card><SectionTitle title={t("rainfallTrends")} /><Bar data={rainfallData} options={{ responsive: true, plugins: { legend: { display: false } } }} /></Card>
        <Card><SectionTitle title="Prediction History" helper={`Only predictions created by ${session.name} are shown here.`} />
          <div className="mt-4 space-y-3 text-sm">
            {history.length === 0 && <p className="text-stone-500">No prediction history yet for this account.</p>}
            {history.slice(0, 5).map((row) => (
              <div key={row.id} className="rounded-lg border border-green-900/10 p-3 dark:border-stone-700">
                <p><strong>District:</strong> {row.district || "-"}</p>
                <p><strong>Taluk:</strong> {getTalukLabel(row.district, row.taluk) || row.taluk || "-"}</p>
                <p><strong>Village:</strong> {row.village || (officialLocationDataAvailable ? "-" : officialVillageDatasetMessage)}</p>
                <p><strong>{t("crop")}:</strong> {t(`crops.${row.crop}`, row.crop)} | <strong>{t("predictedYield")}:</strong> {row.prediction}</p>
              </div>
            ))}
          </div>
        </Card>
        <Card><SectionTitle title={t("registeredFarmers")} helper={t("registeredFarmersHelper")} />
          <div className="mt-4 space-y-3 text-sm">
            {registeredUsers.length === 0 && <p className="text-stone-500">{t("noRegisteredUsers")}</p>}
            {registeredUsers.map((user) => (
              <div key={user.id} className="rounded-lg border border-green-900/10 p-3 dark:border-stone-700">
                <p><strong>{t("name")}:</strong> {user.name}</p>
                <p><strong>{t("email")}:</strong> {user.email}</p>
                <p><strong>{t("role")}:</strong> {user.role}</p>
                <p><strong>{t("registeredOn")}:</strong> {new Date(user.created_at).toLocaleString()}</p>
              </div>
            ))}
          </div>
        </Card>
        <Card id="login"><SectionTitle eyebrow={t("secureAccess")} title={t("account")} helper={t("loggedInAs", { name: session.name, role: session.role })} /><div className="mt-4"><p className="notice success"><FiShield /> {t("loggedInAs", { name: session.name, role: session.role })}</p><button type="button" className="btn-secondary mt-4" onClick={logout}>{t("logout")}</button></div></Card>
      </div>
      <section className="about-band mx-auto max-w-7xl px-4 pb-10"><Card><SectionTitle title="Project Working" helper="This platform registers farmers, fetches district weather, accepts manual rainfall values, predicts crop yield, stores each user's own prediction history, and monitors ESP32 field sensor data with calibration controls." /></Card></section>
      <footer className="border-t border-green-900/10 px-4 py-6 text-center text-sm text-stone-600 dark:border-stone-800 dark:text-stone-300">{t("footerText")}</footer>
    </main>
  );
}











