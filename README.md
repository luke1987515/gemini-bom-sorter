# gemini-bom-sorter

An AI-powered automation tool using Google Gemini to classify hardware BOM components for Relex reliability prediction.
（利用 Google Gemini AI 自動將硬體 BOM 表元件歸類至 Relex 可靠度預估標準的自動化工具。）

## 🚀 線上免安裝版 (Google Colab)
不需要自己手動開空白 Colab 再慢慢貼程式碼，您可以直接把下面這串網址傳給您的同事：

👉 [點我直接在 Google Colab 開啟 Gemini BOM Sorter](https://colab.research.google.com/github/luke1987515/gemini-bom-sorter/blob/main/gemini-bom-sorter-colab.ipynb)

## 💻 本地端系統需求
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
- 目前免費版 Gemini API (Free Tier) 有每分鐘呼叫次數 (RPM) 的限制（約 15 次/分鐘）。為了避免遇到 `429 RESOURCE_EXHAUSTED` 錯誤，程式碼內部已內建加入 **4 秒的暫停機制 (sleep)**。這會讓處理速度變慢，但能確保穩定免費跑完大量資料。
