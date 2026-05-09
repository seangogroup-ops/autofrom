# -*- coding: utf-8 -*-

# ════════════════════════════════════════════════════════
#  SNGEDU AUTO GOOGLE FORMS  –  v5.3  (Compact 450×500)
#  Thêm: Tự động lấy Gemini API key qua Chrome + lưu local
# ════════════════════════════════════════════════════════

# ─── ẨN CMD NGAY KHI KHỞI ĐỘNG (TRƯỚC MỌI IMPORT) ──────
import sys, os

if sys.platform == "win32":
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    import subprocess as _sp
    _STARTUPINFO = _sp.STARTUPINFO()
    _STARTUPINFO.dwFlags  |= _sp.STARTF_USESHOWWINDOW
    _STARTUPINFO.wShowWindow = 0
    _NO_WINDOW = 0x08000000
else:
    _STARTUPINFO = None
    _NO_WINDOW   = 0

import customtkinter as ctk
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import threading, time, json, re
import urllib.request
import urllib.error
import urllib.parse

# ─── Màu sắc ─────────────────────────────────────────────
ACCENT_BLUE  = "#1a73e8"
ACCENT_GREEN = "#00c851"
ACCENT_RED   = "#ff4444"
ACCENT_NOTE  = "#ffcc00"
ACCENT_AI    = "#9b59b6"
BG_BLACK     = "#000000"
INPUT_BG     = "#0a0a0a"
CARD_BG      = "#0d0d0d"
BORDER_CLR   = "#1f1f1f"

# ─── File lưu API key local ───────────────────────────────
KEY_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemini_key.json")


def _load_saved_key() -> str:
    try:
        if os.path.exists(KEY_FILE):
            with open(KEY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("api_key", "")
    except Exception:
        pass
    return ""


def _save_key(api_key: str):
    try:
        with open(KEY_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": api_key, "saved_at": time.strftime("%Y-%m-%d %H:%M:%S")}, f)
    except Exception as e:
        print(f"[LƯU KEY LỖI]: {e}")


# ═══════════════════════════════════════════════════════
#  JS SCRIPTS
# ═══════════════════════════════════════════════════════
SCAN_PAGE_SCRIPT = r"""
return (function() {
    const groups = document.querySelectorAll('[role="radiogroup"], [role="group"], .Qr7Oae');
    const results = [];
    for (let g of groups) {
        const textInputs = g.querySelectorAll('input[type="text"], input[type="email"], textarea, input.whsOnd, textarea.KHxj8b');
        if (textInputs.length > 0) {
            const labelEl = g.querySelector('[role="heading"], .M7eMe, .freebirdFormviewerComponentsQuestionBaseTitle, label');
            const label = labelEl ? labelEl.innerText.trim() : 'Câu hỏi văn bản';
            results.push({ label: label });
        }
    }
    const txt = el => (el.innerText || el.textContent || '').trim().normalize('NFC');
    const allBtns = Array.from(document.querySelectorAll('[role="button"]'));
    const hasNext   = allBtns.some(el => { const t=txt(el); return t==='Next'||t==='Tiếp'||t==='Tiếp theo'; });
    const hasSubmit = allBtns.some(el => { const t=txt(el); return t==='Submit'||t==='Nộp'||t.startsWith('Gử'); });
    return { questions: results, hasNext: hasNext, hasSubmit: hasSubmit };
})();
"""

CLICK_NEXT_SCRIPT = r"""
return (async function() {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const txt = el => (el.innerText || el.textContent || '').trim().normalize('NFC');
    const allBtns = Array.from(document.querySelectorAll('[role="button"]'));
    const isBack = el => { const t=txt(el); return t==='Back'||t==='Quay lại'; };
    const isNext = el => { const t=txt(el); return t==='Next'||t==='Tiếp'||t==='Tiếp theo'; };
    const nextBtn = allBtns.filter(b => !isBack(b)).find(isNext);
    if (nextBtn) {
        nextBtn.scrollIntoView({ behavior:'smooth', block:'center' });
        await wait(300); nextBtn.click(); return true;
    }
    return false;
})();
"""

DUMMY_FILL_SCRIPT = r"""
return (async function() {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const groups = document.querySelectorAll('[role="radiogroup"], [role="group"], .Qr7Oae');
    for (let g of groups) {
        const radios = g.querySelectorAll('[role="radio"]');
        if (radios.length > 0) {
            if (!Array.from(radios).some(r => r.getAttribute('aria-checked')==='true'))
                { radios[0].click(); await wait(60); }
            continue;
        }
        const checks = g.querySelectorAll('[role="checkbox"]');
        if (checks.length > 0) {
            if (!Array.from(checks).some(c => c.getAttribute('aria-checked')==='true'))
                { checks[0].click(); await wait(60); }
            continue;
        }
        const textInputs = g.querySelectorAll('input[type="text"], input[type="email"], textarea, input.whsOnd, textarea.KHxj8b');
        for (let t of textInputs) {
            if (t.type==='hidden'||t.disabled) continue;
            if (t.value.trim()==='') {
                t.value = 'test';
                t.dispatchEvent(new Event('input', { bubbles: true }));
                await wait(60);
            }
        }
    }
    return true;
})();
"""

FORM_SCRIPT_TPL = r"""
return (async function() {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const customAnswers = {answers};
    const groups = document.querySelectorAll('[role="radiogroup"], [role="group"], .Qr7Oae');
    let textQIdx = 0;
    for (let g of groups) {
        const radios = g.querySelectorAll('[role="radio"]');
        if (radios.length > 0) {
            const done = Array.from(radios).some(r => r.getAttribute('aria-checked')==='true' || r.classList.contains('RDPZE'));
            if (!done) { radios[Math.floor(Math.random()*radios.length)].click(); await wait(80); }
            continue;
        }
        const checks = g.querySelectorAll('[role="checkbox"]');
        if (checks.length > 0) {
            const done = Array.from(checks).some(c => c.getAttribute('aria-checked')==='true' || c.classList.contains('RDPZE'));
            if (!done) {
                const n = Math.ceil(Math.random()*Math.max(1,Math.floor(checks.length/2)));
                Array.from(checks).sort(()=>Math.random()-0.5).slice(0,n).forEach(c=>c.click());
                await wait(80);
            }
            continue;
        }
        const textInputs = g.querySelectorAll('input[type="text"], input[type="email"], textarea, input.whsOnd, textarea.KHxj8b');
        if (textInputs.length > 0) {
            for (let t of textInputs) {
                if (t.type==='hidden'||t.disabled) continue;
                if (t.value.trim()==='') {
                    let chosen = '';
                    if (customAnswers[textQIdx] && customAnswers[textQIdx].length > 0) {
                        const pool = customAnswers[textQIdx];
                        chosen = pool[Math.floor(Math.random()*pool.length)];
                    } else { chosen = "Đã điền tự động"; }
                    t.value = chosen;
                    t.dispatchEvent(new Event('input', { bubbles: true }));
                    t.dispatchEvent(new Event('change', { bubbles: true }));
                    await wait(80);
                }
            }
            textQIdx++;
            continue;
        }
    }
    window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
    await wait(900);
    const body = document.body.innerText || '';
    if (body.indexOf('response has been recorded') !== -1 ||
        body.indexOf('Submit another response') !== -1 ||
        document.querySelector('.freebirdFormviewerViewResponseConfirmationMessage'))
        return 'CONFIRMED';
    const txt = el => (el.innerText || el.textContent || '').trim().normalize('NFC');
    const allBtns = Array.from(document.querySelectorAll('[role="button"]'));
    const isIgnore = el => { const t=txt(el); return t==='Quay lại'||t==='Back'||t==='Xóa'||t==='Clear'; };
    const isSubmit = el => { const t=txt(el); return t==='Submit'||t==='Nộp'||(t.length>=3&&t.charCodeAt(0)===71&&(t.charCodeAt(1)===7917||t.charCodeAt(1)===7903||t.charCodeAt(1)===7911)&&t.charCodeAt(2)===105); };
    const isNext = el => { const t=txt(el); return t==='Next'||t==='Tiếp'||t==='Tiếp theo'; };
    const valid = allBtns.filter(b => !isIgnore(b));
    const submitBtn = valid.find(isSubmit);
    const nextBtn   = valid.find(isNext);
    if (submitBtn) { submitBtn.scrollIntoView({ behavior:'smooth', block:'center' }); await wait(400); submitBtn.click(); return 'SUBMITTED'; }
    if (nextBtn)   { nextBtn.scrollIntoView({ behavior:'smooth', block:'center' });   await wait(400); nextBtn.click();   return 'NEXT'; }
    return 'NO_BUTTON';
})();
"""


# ═══════════════════════════════════════════════════════
#  FREE AI CALLER
# ═══════════════════════════════════════════════════════

def _parse_lines_static(raw: str, n: int) -> list:
    pattern = re.compile(r"^[\s\-*•.。·\d）)\]]+")
    result  = []
    for line in raw.splitlines():
        cleaned = pattern.sub("", line).strip()
        if cleaned:
            result.append(cleaned)
        if len(result) >= n:
            break
    while len(result) < n:
        result.append(f"Câu trả lời {len(result)+1}")
    return result


def _make_prompt(label: str, n: int, context: str = "") -> str:
    ctx = f"Ngữ cảnh form: {context}\n" if context else ""
    return (
        f"{ctx}Câu hỏi trong form khảo sát: '{label}'\n"
        f"Nhiệm vụ: Đóng vai người dùng thực tế, sinh ĐÚNG {n} câu trả lời "
        f"tự nhiên, đa dạng bằng tiếng Việt.\n"
        f"QUY TẮC BẮT BUỘC:\n"
        f"- Mỗi câu trả lời trên MỘT dòng riêng biệt\n"
        f"- KHÔNG đánh số thứ tự\n"
        f"- KHÔNG gạch đầu dòng\n"
        f"- KHÔNG giải thích thêm\n"
        f"- Chỉ trả về đúng {n} dòng nội dung"
    )


def _http_post(url: str, payload: dict, headers: dict, timeout: int = 20) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = json.loads(e.read().decode("utf-8"))
            msg = str(detail)
        except Exception:
            msg = e.reason
        raise RuntimeError(f"HTTP {e.code}: {msg}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URL error: {e.reason}")
    except Exception as e:
        raise RuntimeError(str(e))


def _try_openrouter(prompt: str, api_key: str, timeout: int = 20) -> str:
    data = _http_post(
        "https://openrouter.ai/api/v1/chat/completions",
        {
            "model": "mistralai/mistral-7b-instruct:free",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
        },
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://sngedu.app",
            "X-Title": "SNGEDU",
        },
        timeout
    )
    return data["choices"][0]["message"]["content"]


def _try_groq(prompt: str, api_key: str, timeout: int = 20) -> str:
    data = _http_post(
        "https://api.groq.com/openai/v1/chat/completions",
        {
            "model": "llama3-8b-8192",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.9,
        },
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        timeout
    )
    return data["choices"][0]["message"]["content"]


def _try_together(prompt: str, api_key: str, timeout: int = 20) -> str:
    data = _http_post(
        "https://api.together.xyz/v1/chat/completions",
        {
            "model": "mistralai/Mistral-7B-Instruct-v0.2",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.9,
        },
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        timeout
    )
    return data["choices"][0]["message"]["content"]


def _try_mistral(prompt: str, api_key: str, timeout: int = 20) -> str:
    data = _http_post(
        "https://api.mistral.ai/v1/chat/completions",
        {
            "model": "mistral-tiny",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.9,
        },
        {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        timeout
    )
    return data["choices"][0]["message"]["content"]


def _try_huggingface(prompt: str, timeout: int = 25) -> str:
    url = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
    body = json.dumps({"inputs": prompt, "parameters": {"max_new_tokens": 300}}).encode("utf-8")
    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list):
                raw = data[0].get("generated_text", "")
            else:
                raw = data.get("generated_text", str(data))
            if prompt[:30] in raw:
                raw = raw[raw.find(prompt[:30]) + len(prompt):]
            return raw.strip()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HuggingFace HTTP {e.code}")
    except Exception as e:
        raise RuntimeError(str(e))


_FALLBACK_TEMPLATES = {
    "tên": ["Nguyễn Văn An", "Trần Thị Bích", "Lê Minh Tuấn", "Phạm Thu Hà", "Hoàng Đức Mạnh"],
    "họ":  ["Nguyễn Văn An", "Trần Thị Bích", "Lê Minh Tuấn", "Phạm Thu Hà", "Hoàng Đức Mạnh"],
    "email": ["user123@gmail.com", "example@yahoo.com", "test.user@outlook.com", "info@sngedu.vn", "hello@email.com"],
    "số điện": ["0901234567", "0912345678", "0987654321", "0356789012", "0778901234"],
    "phone":   ["0901234567", "0912345678", "0987654321", "0356789012", "0778901234"],
    "địa chỉ": ["123 Đường Lê Lợi, Q.1", "456 Nguyễn Huệ, Q.3", "789 Trần Phú, Đà Nẵng", "12 Hàng Bài, Hà Nội", "88 Lý Thường Kiệt, HCM"],
    "tuổi":    ["18", "20", "22", "25", "28", "30", "35"],
    "nghề":    ["Học sinh", "Sinh viên", "Nhân viên văn phòng", "Giáo viên", "Kỹ sư", "Bác sĩ"],
    "ý kiến":  ["Rất tốt", "Tốt", "Bình thường", "Cần cải thiện thêm", "Hài lòng với dịch vụ"],
    "nhận xét":["Dịch vụ tốt, sẽ quay lại", "Cần cải thiện thêm", "Rất hài lòng", "Khá ổn, có thể tốt hơn", "Tuyệt vời"],
    "góp ý":   ["Cần cải thiện giao diện", "Thêm nhiều tính năng hơn", "Tốt rồi, giữ nguyên", "Nên có thêm hỗ trợ tiếng Việt", "Rất hài lòng"],
    "lý do":   ["Vì tiện lợi và nhanh chóng", "Được bạn bè giới thiệu", "Tìm kiếm trên mạng", "Quảng cáo hấp dẫn", "Giá cả phải chăng"],
    "mô tả":   ["Rất tốt và chuyên nghiệp", "Bình thường, cần cải thiện", "Xuất sắc, vượt kỳ vọng", "Ổn, đáp ứng nhu cầu cơ bản", "Tốt, sẽ giới thiệu cho bạn bè"],
    "default": ["Rất hài lòng", "Tốt", "Bình thường", "Cần cải thiện", "Xuất sắc",
                "Đồng ý", "Không đồng ý", "Có", "Không", "Tuỳ trường hợp",
                "Rất đồng ý", "Phần lớn đồng ý", "Trung lập", "Phần lớn không đồng ý"]
}


def _fallback_generate(label: str, n: int) -> list:
    label_lower = label.lower()
    pool = _FALLBACK_TEMPLATES["default"]
    for key, answers in _FALLBACK_TEMPLATES.items():
        if key != "default" and key in label_lower:
            pool = answers
            break
    import random
    pool_ext = pool * ((n // len(pool)) + 2)
    random.shuffle(pool_ext)
    return pool_ext[:n]


class FreeAICaller:
    def __init__(self, model: str = "auto", timeout: int = 25,
                 openrouter_key: str = "", groq_key: str = "",
                 together_key: str = "", mistral_key: str = ""):
        self.model         = model
        self.timeout       = timeout
        self.openrouter_key = openrouter_key.strip()
        self.groq_key      = groq_key.strip()
        self.together_key  = together_key.strip()
        self.mistral_key   = mistral_key.strip()
        self._last_provider = "—"

    def _call(self, prompt: str) -> str:
        errors = []
        try:
            result = _try_huggingface(prompt, timeout=self.timeout)
            if result.strip():
                self._last_provider = "HuggingFace"
                return result
        except Exception as e:
            errors.append(f"HuggingFace: {e}")

        if self.openrouter_key:
            try:
                result = _try_openrouter(prompt, self.openrouter_key, self.timeout)
                if result.strip():
                    self._last_provider = "OpenRouter"
                    return result
            except Exception as e:
                errors.append(f"OpenRouter: {e}")

        if self.groq_key:
            try:
                result = _try_groq(prompt, self.groq_key, self.timeout)
                if result.strip():
                    self._last_provider = "Groq"
                    return result
            except Exception as e:
                errors.append(f"Groq: {e}")

        if self.together_key:
            try:
                result = _try_together(prompt, self.together_key, self.timeout)
                if result.strip():
                    self._last_provider = "Together AI"
                    return result
            except Exception as e:
                errors.append(f"Together: {e}")

        if self.mistral_key:
            try:
                result = _try_mistral(prompt, self.mistral_key, self.timeout)
                if result.strip():
                    self._last_provider = "Mistral"
                    return result
            except Exception as e:
                errors.append(f"Mistral: {e}")

        raise RuntimeError("Tất cả API đều lỗi:\n" + " | ".join(errors))

    def generate_answers(self, label: str, n: int, context: str = "") -> list:
        prompt = _make_prompt(label, n, context)
        try:
            raw = self._call(prompt)
            return _parse_lines_static(raw, n)
        except Exception:
            self._last_provider = "Fallback nội bộ"
            return _fallback_generate(label, n)

    def test_connection(self) -> str:
        raw = self._call("Trả lời đúng 1 chữ: OK")
        return f"{raw.strip()[:20]} [{self._last_provider}]"


# ═══════════════════════════════════════════════════════
#  GEMINI CALLER
# ═══════════════════════════════════════════════════════
class GeminiCaller:
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

    def __init__(self, api_key: str, model: str, timeout: int = 30):
        self.api_key = api_key
        self.model   = model
        self.timeout = timeout

    def _call(self, prompt: str) -> str:
        url = self.BASE_URL.format(model=self.model, key=self.api_key)
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.9, "maxOutputTokens": 1024}
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["candidates"][0]["content"]["parts"][0]["text"]
        except urllib.error.HTTPError as e:
            try:
                err_body = json.loads(e.read().decode("utf-8"))
                msg = err_body.get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            raise RuntimeError(f"HTTP {e.code}: {msg}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Lỗi mạng: {e.reason}")

    @staticmethod
    def _parse_lines(raw: str, n: int) -> list:
        pattern = re.compile(r"^[\s\-*•.。·\d）)\]]+")
        result  = []
        for line in raw.splitlines():
            cleaned = pattern.sub("", line).strip()
            if cleaned:
                result.append(cleaned)
            if len(result) >= n:
                break
        while len(result) < n:
            result.append(f"Câu trả lời {len(result)+1}")
        return result

    def generate_answers(self, label: str, n: int, context: str = "") -> list:
        ctx = f"Ngữ cảnh form: {context}\n" if context else ""
        prompt = (
            f"{ctx}Câu hỏi trong form khảo sát: '{label}'\n"
            f"Nhiệm vụ: Đóng vai người dùng thực tế, sinh ĐÚNG {n} câu trả lời "
            f"tự nhiên, đa dạng bằng tiếng Việt.\n"
            f"QUY TẮC BẮT BUỘC:\n"
            f"- Mỗi câu trả lời trên MỘT dòng riêng biệt\n"
            f"- KHÔNG đánh số thứ tự\n"
            f"- KHÔNG gạch đầu dòng\n"
            f"- KHÔNG giải thích thêm\n"
            f"- Chỉ trả về đúng {n} dòng nội dung"
        )
        raw = self._call(prompt)
        return self._parse_lines(raw, n)

    def test_connection(self) -> str:
        raw = self._call("Trả lời đúng 1 chữ: OK")
        return raw.strip()[:30]


# ═══════════════════════════════════════════════════════
#  TÌM CHROME PROFILE THẬT CỦA USER
# ═══════════════════════════════════════════════════════

def _find_chrome_user_data() -> str:
    if sys.platform == "win32":
        base = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    else:
        base = os.path.expanduser("~/.config/google-chrome")

    if os.path.isdir(base):
        return base
    if sys.platform == "win32":
        alt = os.path.expandvars(r"%LOCALAPPDATA%\Chromium\User Data")
    elif sys.platform == "darwin":
        alt = os.path.expanduser("~/Library/Application Support/Chromium")
    else:
        alt = os.path.expanduser("~/.config/chromium")
    if os.path.isdir(alt):
        return alt
    return ""


def _copy_chrome_profile_to_temp(src_user_data: str, profile: str = "Default") -> str:
    import shutil, tempfile
    tmp_dir = tempfile.mkdtemp(prefix="sngedu_chrome_")
    src_profile = os.path.join(src_user_data, profile)
    dst_profile  = os.path.join(tmp_dir, profile)
    os.makedirs(dst_profile, exist_ok=True)

    copy_items = ["Cookies", "Login Data", "Web Data",
                  "Preferences", "Secure Preferences",
                  "Extension Cookies", "Network Persistent State"]
    for item in copy_items:
        src_item = os.path.join(src_profile, item)
        if os.path.isfile(src_item):
            try:
                shutil.copy2(src_item, os.path.join(dst_profile, item))
            except Exception:
                pass
    ls_src = os.path.join(src_user_data, "Local State")
    if os.path.isfile(ls_src):
        try:
            shutil.copy2(ls_src, os.path.join(tmp_dir, "Local State"))
        except Exception:
            pass
    return tmp_dir


def _make_stealth_options(user_data_dir: str = "", profile: str = "Default") -> Options:
    opts = Options()
    if user_data_dir:
        opts.add_argument(f"--user-data-dir={user_data_dir}")
        opts.add_argument(f"--profile-directory={profile}")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--log-level=3")
    opts.add_argument("--silent")
    opts.add_argument("--start-maximized")
    opts.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    opts.add_experimental_option("useAutomationExtension", False)
    return opts


# ═══════════════════════════════════════════════════════
#  TỰ ĐỘNG LẤY GEMINI API KEY QUA CHROME PROFILE THẬT
# ═══════════════════════════════════════════════════════

def _auto_fetch_gemini_key(status_callback=None) -> str:
    def _cb(msg):
        if status_callback:
            status_callback(msg)
        print(f"[KEY FETCH] {msg}")

    import shutil as _shutil
    _tmp_dir = None
    _src_data = _find_chrome_user_data()
    if _src_data:
        _cb("Tìm thấy Chrome profile, đang copy cookie sang thư mục tạm...")
        try:
            _tmp_dir = _copy_chrome_profile_to_temp(_src_data, "Default")
            _cb("✓ Đã copy profile")
        except Exception as _e:
            _cb(f"Không copy được profile ({_e}), dùng profile trắng...")
            _tmp_dir = None
    else:
        _cb("Không tìm thấy Chrome, dùng profile trắng...")

    opts = _make_stealth_options(user_data_dir=_tmp_dir or "", profile="Default")

    svc = Service(ChromeDriverManager().install())
    if sys.platform == "win32":
        svc.creation_flags = _NO_WINDOW
        svc.startupinfo    = _STARTUPINFO

    drv = None
    try:
        drv = webdriver.Chrome(service=svc, options=opts)

        drv.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
            "source": """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'languages', { get: () => ['vi-VN', 'vi', 'en-US', 'en'] });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
                window.chrome = { runtime: {} };
            """
        })

        _cb("Đang kiểm tra trạng thái đăng nhập Google...")
        drv.get("https://myaccount.google.com/")
        time.sleep(3)

        cur = drv.current_url
        already_logged = (
            "myaccount.google.com" in cur and
            "signin" not in cur and
            "ServiceLogin" not in cur
        )

        if not already_logged:
            _cb("⚠️ Chưa đăng nhập. Vui lòng đăng nhập Google trong cửa sổ Chrome...")
            drv.get("https://accounts.google.com/signin/v2/identifier")
            time.sleep(2)

            deadline = time.time() + 180
            logged_in = False
            dots = 0
            while time.time() < deadline:
                time.sleep(2)
                dots += 1
                remaining = int(deadline - time.time())
                _cb(f"⏳ Chờ đăng nhập... còn {remaining}s {'.' * (dots % 4)}")
                try:
                    cur2 = drv.current_url
                    if (
                        "myaccount.google.com" in cur2 or
                        "google.com/u/" in cur2 or
                        ("accounts.google.com" not in cur2 and "signin" not in cur2 and "ServiceLogin" not in cur2)
                    ):
                        logged_in = True
                        break
                except Exception:
                    break

            if not logged_in:
                raise RuntimeError("Hết thời gian chờ đăng nhập (3 phút). Vui lòng thử lại.")
        else:
            _cb("✓ Đã đăng nhập Google sẵn!")

        time.sleep(1)

        _cb("Đang mở AI Studio API key page...")
        drv.get("https://aistudio.google.com/apikey")
        time.sleep(6)

        wait = WebDriverWait(drv, 30)

        _cb("Đang tìm nút tạo API key...")
        create_btn = None
        btn_xpaths = [
            "//button[contains(., 'Create API key')]",
            "//button[contains(., 'Get API key')]",
            "//button[contains(., 'Create API Key')]",
            "//button[contains(., 'Tạo khóa API')]",
            "//*[@aria-label='Create API key']",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'create api')]",
            "//button[contains(translate(.,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'get api key')]",
        ]
        for xp in btn_xpaths:
            try:
                el = wait.until(EC.element_to_be_clickable((By.XPATH, xp)))
                create_btn = el
                break
            except Exception:
                continue

        if not create_btn:
            try:
                all_btns = drv.find_elements(By.TAG_NAME, "button")
                for b in all_btns:
                    if b.is_displayed() and "key" in b.text.lower():
                        create_btn = b
                        break
            except Exception:
                pass

        if not create_btn:
            raise RuntimeError(
                "Không tìm thấy nút tạo API key trên trang AI Studio. "
                "Có thể Google đã thay đổi giao diện. "
                "Hãy vào aistudio.google.com/apikey và copy key thủ công."
            )

        _cb("Đang click tạo API key...")
        drv.execute_script("arguments[0].scrollIntoView({block:'center'});", create_btn)
        time.sleep(0.5)
        drv.execute_script("arguments[0].click();", create_btn)
        time.sleep(3)

        try:
            dialog_xpaths = [
                "//button[contains(., 'Create API key in new project')]",
                "//button[contains(., 'Create in new project')]",
                "//button[contains(., 'Tạo khóa API trong dự án mới')]",
                "//mat-dialog-container//button[last()]",
                "//*[@role='dialog']//button[last()]",
            ]
            for dxp in dialog_xpaths:
                try:
                    dbtn = WebDriverWait(drv, 4).until(
                        EC.element_to_be_clickable((By.XPATH, dxp)))
                    _cb("Đang xử lý dialog chọn project...")
                    drv.execute_script("arguments[0].click();", dbtn)
                    time.sleep(3)
                    break
                except Exception:
                    continue
        except Exception:
            pass

        _cb("Đang đọc API key từ trang...")
        time.sleep(2)
        api_key = None

        try:
            api_key = drv.execute_script("""
                const t = document.body.innerText || '';
                const m = t.match(/AIza[0-9A-Za-z_\\-]{35,}/);
                return m ? m[0] : null;
            """)
        except Exception:
            pass

        if not api_key:
            try:
                api_key = drv.execute_script("""
                    const inputs = document.querySelectorAll('input, [data-value]');
                    for (let el of inputs) {
                        const v = el.value || el.getAttribute('data-value') || '';
                        const m = v.match(/AIza[0-9A-Za-z_\\-]{35,}/);
                        if (m) return m[0];
                    }
                    return null;
                """)
            except Exception:
                pass

        if not api_key:
            try:
                elements = drv.find_elements(By.XPATH, "//*[contains(text(),'AIza')]")
                for el in elements:
                    m = re.search(r'AIza[0-9A-Za-z_\-]{35,}', el.text)
                    if m:
                        api_key = m.group(0)
                        break
            except Exception:
                pass

        if not api_key:
            try:
                copy_btns = drv.find_elements(
                    By.XPATH,
                    "//button[contains(@aria-label,'opy') or contains(@title,'opy') or contains(@mattooltip,'opy')]"
                )
                for cb in copy_btns:
                    if cb.is_displayed():
                        drv.execute_script("arguments[0].click();", cb)
                        time.sleep(0.8)
                        raw = drv.execute_script("""
                            return new Promise(resolve => {
                                navigator.clipboard.readText().then(t => resolve(t)).catch(() => resolve(''));
                            });
                        """)
                        if raw and "AIza" in str(raw):
                            m = re.search(r'AIza[0-9A-Za-z_\-]{35,}', str(raw))
                            if m:
                                api_key = m.group(0)
                                break
            except Exception:
                pass

        if not api_key:
            raise RuntimeError(
                "Không đọc được API key tự động.\n"
                "Vui lòng vào aistudio.google.com/apikey → copy key → dán thủ công vào ô API Key."
            )

        if not re.match(r'^AIza[0-9A-Za-z_\-]{35,}$', api_key):
            raise RuntimeError(f"Key có định dạng không hợp lệ: {api_key[:20]}...")

        _cb(f"✓ Lấy key thành công!")
        return api_key

    finally:
        if drv:
            try:
                drv.quit()
            except Exception:
                pass
        try:
            if _tmp_dir and os.path.isdir(_tmp_dir):
                import shutil as _sh2
                _sh2.rmtree(_tmp_dir, ignore_errors=True)
        except Exception:
            pass


# ═══════════════════════════════════════════════════════
#  GUI CHÍNH  –  Compact 450 × 500
# ═══════════════════════════════════════════════════════
class SngEduAuto(ctk.CTk):
    # ── Kích thước cố định ──────────────────────────────
    WIN_W = 450
    WIN_H = 500

    def __init__(self):
        super().__init__()
        self.title("SNGEDU – AUTO GOOGLE FORMS  v5.3")
        self.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self.configure(fg_color=BG_BLACK)
        self.resizable(False, False)

        self.driver              = None
        self._stop_flag          = False
        self.text_answers        = {}
        self._answer_textboxes   = {}
        self._question_info      = []
        self._scan_headless_var  = ctk.BooleanVar(value=False)

        # ── TabView: giảm chiều rộng/cao theo cửa sổ ──
        self.tabview = ctk.CTkTabview(
            self,
            width=self.WIN_W - 16,
            height=self.WIN_H - 16,
            fg_color=BG_BLACK,
            segmented_button_fg_color="#111111",
            segmented_button_selected_color=ACCENT_BLUE,
            segmented_button_selected_hover_color="#155cb0",
            segmented_button_unselected_color="#111111",
            segmented_button_unselected_hover_color="#1a1a1a",
            text_color="#ffffff",
            border_color=BORDER_CLR, border_width=1)
        self.tabview.pack(padx=8, pady=8, fill="both", expand=True)
        self.tabview.add("⚙️  Tự động")
        self.tabview.add("✏️  Câu hỏi")
        self.tabview.add("🤖  AI")

        self._build_main_tab()
        self._build_text_tab()
        self._build_ai_tab()

        self._load_saved_key_on_start()

    # ─────────────────────────────────────────────────────
    #  LOAD KEY KHI KHỞI ĐỘNG
    # ─────────────────────────────────────────────────────
    def _load_saved_key_on_start(self):
        saved = _load_saved_key()
        if saved:
            self.ai_type_var.set("gemini")
            self._on_ai_type_change()
            self.api_key_entry.delete(0, "end")
            self.api_key_entry.insert(0, saved)
            self.ai_status_lbl.configure(
                text=f"✓ Đã load key: {saved[:12]}...",
                text_color=ACCENT_GREEN)

    # ─────────────────────────────────────────────────────
    #  TAB 1: TỰ ĐỘNG HÓA  (compact)
    # ─────────────────────────────────────────────────────
    def _build_main_tab(self):
        tab = self.tabview.tab("⚙️  Tự động")

        # Tiêu đề nhỏ hơn
        ctk.CTkLabel(tab, text="SNGEDU AUTO FORM",
                     font=("Georgia", 18, "bold"), text_color="#FFFFFF").pack(pady=(10, 2))
        ctk.CTkLabel(tab,
                     text="Form chỉ hoạt động khi không đăng nhập Google",
                     font=("Arial", 9, "bold"), text_color=ACCENT_NOTE).pack(pady=(0, 8))

        # URL input – width vừa khung
        self.url_input = ctk.CTkEntry(
            tab, width=400, height=36,
            placeholder_text="Dán đường dẫn Google Form...",
            font=("Arial", 11), fg_color=INPUT_BG,
            border_color=BORDER_CLR, border_width=2, corner_radius=10)
        self.url_input.pack(pady=(0, 6))

        # Scan row
        scan_row = ctk.CTkFrame(tab, fg_color="transparent")
        scan_row.pack(pady=(0, 4))

        self.scan_btn = ctk.CTkButton(
            scan_row, text="🔍  Quét câu hỏi văn bản",
            command=self.scan_questions, height=32, width=240,
            font=("Arial", 11, "bold"), fg_color="#1a1a1a", hover_color="#2a2a2a",
            border_color=ACCENT_BLUE, border_width=1, corner_radius=8)
        self.scan_btn.pack(side="left", padx=(0, 6))

        ctk.CTkCheckBox(scan_row, text="Ngầm",
            variable=self._scan_headless_var,
            font=("Arial", 10), text_color="#aaaaaa",
            fg_color=ACCENT_BLUE, hover_color="#155cb0",
            checkmark_color="#ffffff", border_color="#333333",
            width=70).pack(side="left")

        self.scan_page_lbl = ctk.CTkLabel(tab, text="",
                                           font=("Arial", 9), text_color="#555555")
        self.scan_page_lbl.pack(pady=(0, 6))

        # Số lần
        count_frame = ctk.CTkFrame(tab, fg_color="transparent")
        count_frame.pack(pady=(0, 8))
        ctk.CTkLabel(count_frame, text="Số lần:",
                     font=("Arial", 12), text_color="#aaaaaa").pack(side="left", padx=(0, 8))
        ctk.CTkButton(count_frame, text="−", width=30, height=30,
            font=("Arial", 16, "bold"), fg_color="#1a1a1a",
            hover_color="#2a2a2a", corner_radius=6,
            command=self.decrement).pack(side="left")
        self.count_var = ctk.StringVar(value="1")
        ctk.CTkEntry(count_frame, width=52, height=30,
            textvariable=self.count_var, font=("Arial", 13, "bold"),
            fg_color=INPUT_BG, border_color="#333333",
            border_width=2, corner_radius=6, justify="center").pack(side="left", padx=4)
        ctk.CTkButton(count_frame, text="+", width=30, height=30,
            font=("Arial", 16, "bold"), fg_color="#1a1a1a",
            hover_color="#2a2a2a", corner_radius=6,
            command=self.increment).pack(side="left")

        self.headless_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(tab, text="Chạy ngầm khi nộp (ẩn trình duyệt)",
            variable=self.headless_var, font=("Arial", 11),
            text_color="#aaaaaa", fg_color=ACCENT_BLUE,
            hover_color="#155cb0", checkmark_color="#ffffff",
            border_color="#333333").pack(pady=(0, 10))

        # Nút BẮT ĐẦU / DỪNG
        btn_frame = ctk.CTkFrame(tab, fg_color="transparent")
        btn_frame.pack(pady=(0, 6))
        ctk.CTkButton(btn_frame, text="BẮT ĐẦU TỰ ĐỘNG HÓA",
            command=self.start_thread, height=40, width=220,
            font=("Arial", 13, "bold"),
            fg_color=ACCENT_BLUE, hover_color="#155cb0",
            corner_radius=10).pack(side="left", padx=(0, 8))
        ctk.CTkButton(btn_frame, text="DỪNG", command=self.stop,
            height=40, width=76, font=("Arial", 12, "bold"),
            fg_color="#333333", hover_color="#555555",
            corner_radius=10).pack(side="left")

        self.progress_lbl = ctk.CTkLabel(tab, text="",
            font=("Arial", 10), text_color="#888888")
        self.progress_lbl.pack()
        self.progress_bar = ctk.CTkProgressBar(tab, width=400, height=6,
            corner_radius=3, fg_color="#1a1a1a", progress_color=ACCENT_BLUE)
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(2, 0))
        self.status_lbl = ctk.CTkLabel(tab, text="Hệ thống: Sẵn sàng",
            font=("Arial", 10), text_color="#666666")
        self.status_lbl.pack(pady=(6, 0))

    # ─────────────────────────────────────────────────────
    #  TAB 2: CÂU HỎI & TRẢ LỜI  (compact)
    # ─────────────────────────────────────────────────────
    def _build_text_tab(self):
        tab = self.tabview.tab("✏️  Câu hỏi")
        hdr = ctk.CTkFrame(tab, fg_color="transparent")
        hdr.pack(fill="x", padx=8, pady=(8, 2))
        ctk.CTkLabel(hdr, text="Câu hỏi & Câu trả lời",
                     font=("Georgia", 14, "bold"), text_color="#FFFFFF").pack(side="left")
        self.gen_all_btn = ctk.CTkButton(hdr, text="✨ AI GET",
            command=self.ai_generate_all, height=28, width=110,
            font=("Arial", 10, "bold"),
            fg_color=ACCENT_AI, hover_color="#7d3c98", corner_radius=6)
        self.gen_all_btn.pack(side="right")

        ctk.CTkLabel(tab,
            text="Nhiều câu trả lời, cách nhau bằng dấu phẩy  ·  AI tự sinh nếu bật",
            font=("Arial", 9), text_color="#555555").pack(pady=(0, 4))

        self.questions_frame = ctk.CTkScrollableFrame(tab, fg_color=CARD_BG,
            border_color=BORDER_CLR, border_width=1, corner_radius=8)
        self.questions_frame.pack(padx=6, pady=(0, 6), fill="both", expand=True)
        ctk.CTkLabel(self.questions_frame,
            text="Chưa có câu hỏi – bấm 🔍 Quét ở tab Tự động",
            font=("Arial", 11), text_color="#444444",
            justify="center").pack(expand=True, pady=60)

        foot = ctk.CTkFrame(tab, fg_color="transparent")
        foot.pack(fill="x", padx=8, pady=(0, 6))
        ctk.CTkButton(foot, text="💾  Lưu",
            command=self.save_answers, height=32, width=120,
            font=("Arial", 11, "bold"),
            fg_color=ACCENT_BLUE, hover_color="#155cb0",
            corner_radius=6).pack(side="left")
        self.save_status = ctk.CTkLabel(foot, text="",
            font=("Arial", 10), text_color="#666666")
        self.save_status.pack(side="left", padx=8)

    # ─────────────────────────────────────────────────────
    #  TAB 3: AI CONFIG  (compact, scroll)
    # ─────────────────────────────────────────────────────
    def _build_ai_tab(self):
        tab = self.tabview.tab("🤖  AI")

        self.ai_type_var = ctk.StringVar(value="gemini")

        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent",
                                        border_width=0, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=0, pady=0)

        ctk.CTkLabel(scroll, text="Cấu hình Gemini AI",
                     font=("Georgia", 15, "bold"), text_color="#FFFFFF").pack(pady=(10, 6))

        # ── Bật/tắt AI ──
        toggle_card = ctk.CTkFrame(scroll, fg_color="#0f0f0f",
                                   border_color="#2a2a2a", border_width=1, corner_radius=8)
        toggle_card.pack(fill="x", padx=12, pady=(0, 6))
        inner = ctk.CTkFrame(toggle_card, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(inner, text="🤖  Bật AI",
                     font=("Arial", 12, "bold"), text_color="#dddddd").pack(side="left")
        self.ai_enabled_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(inner, text="", variable=self.ai_enabled_var,
                      progress_color=ACCENT_AI,
                      command=self._on_ai_toggle).pack(side="right")

        # ── API Key ──
        key_card = ctk.CTkFrame(scroll, fg_color="#0f0f0f",
                                border_color="#2a2a2a", border_width=1, corner_radius=8)
        key_card.pack(fill="x", padx=12, pady=(0, 6))
        key_inner = ctk.CTkFrame(key_card, fg_color="transparent")
        key_inner.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(key_inner, text="Gemini API Key",
                     font=("Arial", 11, "bold"), text_color="#aaaaaa",
                     anchor="w").pack(fill="x")

        self.api_key_entry = ctk.CTkEntry(
            key_inner, height=36,
            placeholder_text="AIzaSy...",
            font=("Arial", 11), fg_color=INPUT_BG,
            border_color="#2a2a2a", border_width=1, corner_radius=6, show="•")
        self.api_key_entry.pack(fill="x", pady=(3, 4))

        key_row = ctk.CTkFrame(key_inner, fg_color="transparent")
        key_row.pack(fill="x", pady=(0, 4))

        self.show_key_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(key_row, text="Hiện key",
                        variable=self.show_key_var,
                        font=("Arial", 10), text_color="#666666",
                        fg_color=ACCENT_BLUE,
                        command=self._toggle_show_key).pack(side="left")

        self.auto_key_btn = ctk.CTkButton(
            key_row,
            text="🔑  Tự lấy Key",
            command=self._start_auto_key_fetch,
            height=28, width=150,
            font=("Arial", 10, "bold"),
            fg_color="#1a1a1a", hover_color="#2a2a2a",
            border_color=ACCENT_NOTE, border_width=1, corner_radius=6)
        self.auto_key_btn.pack(side="right")

        self.key_fetch_lbl = ctk.CTkLabel(
            key_inner, text="",
            font=("Arial", 9), text_color="#888888",
            wraplength=380, justify="left")
        self.key_fetch_lbl.pack(fill="x", pady=(0, 2))

        # Model
        ctk.CTkLabel(key_inner, text="Model Gemini",
                     font=("Arial", 11, "bold"), text_color="#aaaaaa",
                     anchor="w").pack(fill="x", pady=(4, 0))
        self.model_var = ctk.StringVar(value="gemini-1.5-flash")
        ctk.CTkComboBox(key_inner, variable=self.model_var,
            values=["gemini-1.5-flash", "gemini-2.0-flash",
                    "gemini-1.5-pro", "gemini-pro"],
            font=("Arial", 11), fg_color="#1a1a1a",
            button_color="#222222").pack(fill="x", pady=(3, 0))

        # ── Số câu ──
        count_card = ctk.CTkFrame(scroll, fg_color="#0f0f0f",
                                  border_color="#2a2a2a", border_width=1, corner_radius=8)
        count_card.pack(fill="x", padx=12, pady=(0, 6))
        count_inner = ctk.CTkFrame(count_card, fg_color="transparent")
        count_inner.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(count_inner, text="Số câu AI sinh mỗi câu hỏi:",
                     font=("Arial", 11), text_color="#aaaaaa").pack(side="left", padx=(0, 8))
        self.ai_count_var = ctk.StringVar(value="5")
        ctk.CTkEntry(count_inner, width=50, height=28,
                     textvariable=self.ai_count_var, justify="center").pack(side="left")

        # ── Ngữ cảnh ──
        ctx_card = ctk.CTkFrame(scroll, fg_color="#0f0f0f",
                                border_color="#2a2a2a", border_width=1, corner_radius=8)
        ctx_card.pack(fill="x", padx=12, pady=(0, 6))
        ctx_inner = ctk.CTkFrame(ctx_card, fg_color="transparent")
        ctx_inner.pack(fill="x", padx=12, pady=8)
        ctk.CTkLabel(ctx_inner, text="Ngữ cảnh form (tuỳ chọn)",
                     font=("Arial", 10), text_color="#555555",
                     anchor="w").pack(fill="x")
        self.ai_context_box = ctk.CTkTextbox(ctx_inner, height=48,
            font=("Arial", 11), fg_color=INPUT_BG,
            border_color="#333333", border_width=1, corner_radius=6)
        self.ai_context_box.pack(fill="x", pady=(4, 0))

        # ── Test ──
        test_card = ctk.CTkFrame(scroll, fg_color="#0f0f0f",
                                 border_color="#2a2a2a", border_width=1, corner_radius=8)
        test_card.pack(fill="x", padx=12, pady=(0, 12))
        test_inner = ctk.CTkFrame(test_card, fg_color="transparent")
        test_inner.pack(fill="x", padx=12, pady=8)
        ctk.CTkButton(test_inner, text="🧪  Test kết nối",
            command=self._test_ai, height=32, width=160,
            fg_color="#1a1a1a", border_color=ACCENT_AI,
            border_width=1, corner_radius=6).pack(side="left", padx=(0, 10))
        self.ai_status_lbl = ctk.CTkLabel(test_inner, text="",
            font=("Arial", 10), text_color="#666666")
        self.ai_status_lbl.pack(side="left")

    # ─────────────────────────────────────────────────────
    #  TỰ ĐỘNG LẤY KEY
    # ─────────────────────────────────────────────────────
    def _start_auto_key_fetch(self):
        self.auto_key_btn.configure(state="disabled", text="⏳ Đang lấy...")
        self.key_fetch_lbl.configure(text="Đang khởi động Chrome...", text_color="#aaaaaa")
        threading.Thread(target=self._auto_key_fetch_thread, daemon=True).start()

    def _auto_key_fetch_thread(self):
        def update_status(msg):
            self.after(0, lambda m=msg: self.key_fetch_lbl.configure(
                text=m, text_color="#aaaaaa"))

        try:
            api_key = _auto_fetch_gemini_key(status_callback=update_status)
            _save_key(api_key)

            def _apply():
                self.api_key_entry.delete(0, "end")
                self.api_key_entry.insert(0, api_key)
                self.ai_type_var.set("gemini")
                self._on_ai_type_change()
                self.key_fetch_lbl.configure(
                    text=f"✓ Đã lấy & lưu: {api_key[:12]}...",
                    text_color=ACCENT_GREEN)
                self.auto_key_btn.configure(
                    state="normal", text="🔑  Tự lấy Key")

            self.after(0, _apply)

        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda m=err_msg: self.key_fetch_lbl.configure(
                text=f"✗ {m}", text_color=ACCENT_RED))
            self.after(0, lambda: self.auto_key_btn.configure(
                state="normal", text="🔑  Tự lấy Key"))

    # ─────────────────────────────────────────────────────
    #  AI HELPERS
    # ─────────────────────────────────────────────────────
    def _on_ai_type_change(self):
        pass  # Only Gemini mode in this version

    def _make_caller(self):
        key = self.api_key_entry.get().strip()
        if not key:
            raise ValueError("Chưa nhập API Key Gemini!")
        return GeminiCaller(api_key=key, model=self.model_var.get().strip())

    def _on_ai_toggle(self):
        on = self.ai_enabled_var.get()
        self.ai_status_lbl.configure(
            text="AI đang BẬT ✓" if on else "AI đang TẮT",
            text_color=ACCENT_AI if on else "#666666")

    def _toggle_show_key(self):
        self.api_key_entry.configure(show="" if self.show_key_var.get() else "•")

    def _test_ai(self):
        self.ai_status_lbl.configure(text="Đang kiểm tra...", text_color="#888888")
        threading.Thread(target=self._test_thread, daemon=True).start()

    def _test_thread(self):
        try:
            result = self._make_caller().test_connection()
            self.after(0, lambda: self.ai_status_lbl.configure(
                text=f"✓ OK!  →  {result}",
                text_color=ACCENT_GREEN))
        except RuntimeError as e:
            err = str(e)
            if "429" in err:
                msg = "✗ Rate limit (429)"
            elif "Lỗi mạng" in err:
                msg = f"✗ {err}"
            else:
                msg = f"✗ {err[:50]}"
            self.after(0, lambda m=msg: self.ai_status_lbl.configure(
                text=m, text_color=ACCENT_RED))
        except ValueError as e:
            self.after(0, lambda: self.ai_status_lbl.configure(
                text=f"✗ {e}", text_color=ACCENT_NOTE))
        except Exception as e:
            self.after(0, lambda: self.ai_status_lbl.configure(
                text=f"✗ {str(e)[:50]}", text_color=ACCENT_RED))

    def ai_generate_all(self):
        if not self.ai_enabled_var.get():
            self.gen_all_btn.configure(text="❌ Bật AI trước!")
            self.after(2000, lambda: self.gen_all_btn.configure(text="✨ AI GET"))
            return
        if not self._question_info:
            return
        self.gen_all_btn.configure(state="disabled", text="⏳ Đang sinh...")
        threading.Thread(target=self._gen_all_thread, daemon=True).start()

    def _gen_all_thread(self):
        try:
            caller  = self._make_caller()
            n       = int(self.ai_count_var.get())
            context = self.ai_context_box.get("1.0", "end").strip()
            for q in self._question_info:
                ans = caller.generate_answers(q["label"], n, context)
                self.after(0, lambda i=q["global_idx"], v=", ".join(ans):
                           self._set_textbox(i, v))
        except Exception as e:
            print(f"[GEN ALL LỖI]: {e}")
        finally:
            self.after(0, lambda: self.gen_all_btn.configure(
                state="normal", text="✨ AI GET"))

    def _ai_generate_one(self, idx, label):
        if not self.ai_enabled_var.get():
            return
        def _t():
            try:
                caller  = self._make_caller()
                n       = int(self.ai_count_var.get())
                context = self.ai_context_box.get("1.0", "end").strip()
                ans     = caller.generate_answers(label, n, context)
                self.after(0, lambda: self._set_textbox(idx, ", ".join(ans)))
            except Exception as e:
                print(f"[GEN ONE LỖI]: {e}")
        threading.Thread(target=_t, daemon=True).start()

    def _set_textbox(self, idx, value):
        if idx in self._answer_textboxes:
            self._answer_textboxes[idx].delete("1.0", "end")
            self._answer_textboxes[idx].insert("1.0", value)

    # ─────────────────────────────────────────────────────
    #  SCAN
    # ─────────────────────────────────────────────────────
    def scan_questions(self):
        url = self.url_input.get().strip()
        if not url:
            return
        self.scan_btn.configure(state="disabled", text="⏳ Đang quét...")
        threading.Thread(target=self._scan_thread, args=(url,), daemon=True).start()

    def _scan_thread(self, url):
        try:
            opts = Options()
            if self._scan_headless_var.get():
                opts.add_argument("--headless=new")
            opts.add_argument("--no-sandbox")
            opts.add_argument("--disable-dev-shm-usage")
            opts.add_argument("--disable-gpu")
            opts.add_argument("--log-level=3")
            opts.add_argument("--silent")
            opts.add_experimental_option("excludeSwitches", ["enable-logging"])
            opts.add_experimental_option("useAutomationExtension", False)

            svc = Service(ChromeDriverManager().install())
            if sys.platform == "win32":
                svc.creation_flags = _NO_WINDOW
                svc.startupinfo    = _STARTUPINFO

            drv = webdriver.Chrome(service=svc, options=opts)
            drv.get(url)
            time.sleep(3)

            all_qs, page, g_idx = [], 1, 0
            while True:
                self.after(0, lambda p=page: self.scan_page_lbl.configure(
                    text=f"⏳ Trang {p}..."))
                res = drv.execute_script(SCAN_PAGE_SCRIPT)
                for q in res["questions"]:
                    all_qs.append({"global_idx": g_idx, "page": page, "label": q["label"]})
                    g_idx += 1
                if res["hasNext"]:
                    drv.execute_script(DUMMY_FILL_SCRIPT)
                    time.sleep(0.6)
                    drv.execute_script(CLICK_NEXT_SCRIPT)
                    page += 1
                    time.sleep(2.8)
                else:
                    break
            try: drv.quit()
            except: pass

            self.after(0, lambda: self._populate_questions(all_qs))
            n, p = len(all_qs), page
            self.after(0, lambda: self.scan_page_lbl.configure(
                text=f"✓ {p} trang – {n} câu hỏi"))
        except Exception as e:
            self.after(0, lambda: self.scan_page_lbl.configure(
                text=f"✗ {str(e)[:60]}"))
        finally:
            self.after(0, lambda: self.scan_btn.configure(
                state="normal", text="🔍  Quét câu hỏi văn bản"))

    def _populate_questions(self, questions: list):
        for w in self.questions_frame.winfo_children():
            w.destroy()
        self._answer_textboxes.clear()
        self._question_info = questions

        if not questions:
            ctk.CTkLabel(self.questions_frame,
                         text="Không tìm thấy câu hỏi văn bản.",
                         font=("Arial", 12), text_color="#444444").pack(expand=True, pady=60)
            return

        for q in questions:
            tag  = f"  [T{q['page']}]" if q.get("page") else ""
            card = ctk.CTkFrame(self.questions_frame, fg_color="#131313",
                                border_width=1, corner_radius=6)
            card.pack(fill="x", padx=4, pady=3)

            hdr = ctk.CTkFrame(card, fg_color="transparent")
            hdr.pack(fill="x", padx=8, pady=4)

            q_label_text = q['label']
            ctk.CTkLabel(hdr,
                         text=f"#{q['global_idx']+1}{tag}  –  {q_label_text}",
                         font=("Arial", 11, "bold"), wraplength=280,
                         anchor="w", text_color="#dddddd").pack(side="left")

            ctk.CTkButton(hdr, text="✨", width=26,
                fg_color="#1a1a1a", border_color=ACCENT_AI,
                border_width=1, hover_color="#2d1b40",
                command=lambda i=q['global_idx'], l=q_label_text:
                    self._ai_generate_one(i, l)).pack(side="right", padx=(3, 0))

            ctk.CTkButton(hdr, text="📋", width=26,
                fg_color="#1a1a1a", border_color="#2a6496",
                border_width=1, hover_color="#1a3a56",
                command=lambda lbl=q_label_text: self._copy_question(lbl)
            ).pack(side="right", padx=(3, 0))

            tb = ctk.CTkTextbox(card, height=44, fg_color=INPUT_BG,
                                border_color="#222222", border_width=1)
            tb.pack(fill="x", padx=8, pady=(0, 6))
            self._answer_textboxes[q['global_idx']] = tb

        self.tabview.set("✏️  Câu hỏi")

    def _copy_question(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()

    def save_answers(self):
        self.text_answers.clear()
        for idx, tb in self._answer_textboxes.items():
            raw   = tb.get("1.0", "end").strip()
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            if parts:
                self.text_answers[idx] = parts
        self.save_status.configure(
            text=f"✓ Đã lưu {len(self.text_answers)} câu!",
            text_color=ACCENT_GREEN)
        self.after(3000, lambda: self.save_status.configure(text=""))

    # ─────────────────────────────────────────────────────
    #  HELPERS
    # ─────────────────────────────────────────────────────
    def log(self, msg, color="#666666"):
        self.status_lbl.configure(text=f"Hệ thống: {msg}", text_color=color)

    def set_progress(self, done, total):
        self.progress_bar.set(done / total)
        self.progress_lbl.configure(text=f"{done}/{total}")

    def get_count(self):
        try: return max(1, int(self.count_var.get()))
        except: return 1

    def increment(self): self.count_var.set(str(self.get_count() + 1))
    def decrement(self): self.count_var.set(str(max(1, self.get_count() - 1)))
    def stop(self): self._stop_flag = True

    def _driver_alive(self):
        try: return self.driver and self.driver.current_url is not None
        except: return False

    def _init_driver(self):
        opts = Options()
        if self.headless_var.get(): opts.add_argument("--headless=new")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--log-level=3")
        opts.add_argument("--silent")
        opts.add_experimental_option("excludeSwitches", ["enable-logging"])
        opts.add_experimental_option("useAutomationExtension", False)
        svc = Service(ChromeDriverManager().install())
        if sys.platform == "win32":
            svc.creation_flags = _NO_WINDOW
            svc.startupinfo    = _STARTUPINFO
        self.driver = webdriver.Chrome(service=svc, options=opts)

    def start_thread(self):
        self._stop_flag = False
        url = self.url_input.get().strip()
        if not url: return
        threading.Thread(target=self.run_logic, args=(url,), daemon=True).start()

    def submit_once(self, url: str) -> bool:
        self.driver.get(url)
        js_answers = json.dumps({str(k): v for k, v in self.text_answers.items()})
        js = FORM_SCRIPT_TPL.replace("{answers}", js_answers)
        for _ in range(15):
            time.sleep(2)
            res = self.driver.execute_script(js)
            if res in ("SUBMITTED", "CONFIRMED"): return True
            if res == "NEXT": continue
            break
        return False

    def run_logic(self, url: str):
        total = self.get_count()
        try:
            if not self._driver_alive(): self._init_driver()
            for i in range(total):
                if self._stop_flag: break
                self.after(0, lambda i=i: self.log(
                    f"Đang nộp {i+1}/{total}...", ACCENT_BLUE))
                self.submit_once(url)
                self.after(0, lambda d=i+1, t=total: self.set_progress(d, t))
                time.sleep(0.5)
            self.after(0, lambda: self.log("Hoàn thành!", ACCENT_GREEN))
        except Exception as e:
            self.after(0, lambda: self.log(f"Lỗi: {str(e)[:50]}", ACCENT_RED))


# ═══════════════════════════════════════════════════════
if __name__ == "__main__":
    app = SngEduAuto()
    app.mainloop()