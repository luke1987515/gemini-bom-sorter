# gemini-bom-sorter

An AI-powered automation tool using Google Gemini to classify hardware BOM components for Relex reliability prediction.
（利用 Google Gemini AI 自動將硬體 BOM 表元件歸類至 Relex 可靠度預估標準的自動化工具。）

## 系統需求
- Python 3.8+
- 一把有效的 Gemini API Key

## 安裝步驟

1. 建立並啟動虛擬環境 (建議)：
   ```powershell
   python -m venv venv
   ```
2. 安裝必要的套件：
   ```powershell
   .\venv\Scripts\python.exe -m pip install pandas openpyxl pydantic google-genai
   ```

## 使用教學

1. 設定您的 Gemini API Key 到環境變數中（此方式視窗關閉後即失效，確保安全）：
   ```powershell
   # Windows PowerShell:
   $env:GEMINI_API_KEY="您的_API_KEY_放在這裡"
   
   # Windows CMD:
   set GEMINI_API_KEY=您的_API_KEY_放在這裡
   ```

2. 執行程式：
   ```powershell
   .\venv\Scripts\python.exe gemini-code-1780032449619.py
   ```

3. 程式會彈出視窗讓您選擇來源的 BOM 表 Excel 檔。
   > **注意**：Excel 中必須包含 `PartNumber` 與 `Description` 這兩個欄位。

4. AI 將自動分析並填入 Relex 的主分類、次分類等資訊，結束後會詢問您要將結果另存到哪個路徑。

## 注意事項
- 目前免費版 Gemini API (Free Tier) 有每分鐘呼叫次數 (RPM) 等限制。若您的 BOM 表項目超過免費額度（例如超過 15 筆/分鐘），可能會遇到 `429 RESOURCE_EXHAUSTED` 錯誤。建議升級付費方案或在程式碼中加入延遲 (sleep) 來規避限制。
