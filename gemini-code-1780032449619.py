import os
import json
import pandas as pd
import tkinter as tk
from tkinter import filedialog
from typing import Literal
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

# 1. 初始化 Gemini Client (請確保系統變數已設定 GEMINI_API_KEY)
client = genai.Client()

# 2. 嚴格定義符合 Relex 標準的主類別與次類別限制 (強迫 AI 只能回傳標準字串，避免拼錯字)
class RelexClassification(BaseModel):
    category: Literal[
        "Integrated Circuit", "Semiconductor", "Resistor", "Capacitor", 
        "Inductor", "Rotating Device", "Relay", "Switching Device", 
        "Connection", "Optical Device", "Mechanical Part", "Miscellaneous", "None"
    ] = Field(description="對應 Relex 的主類別 (Category)。若為機構件或不需計算的項目請給 'None'")
    
    subcategory: str = Field(
        description="""對應 Relex 的次類別 (Subcategory)。必須嚴格符合指定名稱，例如：
        - Integrated Circuit: Logic, CGA or ASIC, PAL, PLA, Linear, Microprocessor, Memory, EEPROM, VHSIC/VLSI CMOS, GaAs Digital, Custom
        - Semiconductor: Diode, Microwave Diode, Thyristor, Transistor, Si FET, GaAs FET, Detector, Isolator, Emitter, Laser Diode
        - Resistor: Composition (RC, RCR), Film (RL, RLR, RN, RNR, RM), Film, Power (RD), Accurate, WW (RB, RBR), Lead Mount, WW Power (RW, RWR), Chassis Mount, WW Power (RE, RER), Thermistor (RTH), Network Film (RZ), Surface Mount, General
        - Capacitor: General Ceramic (CK, CKR), Temp Compensat, Ceramic (CC, CCR), Chip, Ceramic (CDR), Paper (CA, CP), Plastic (CFR), Mica (CM, CMR), Glass (CY, CYR), Solid, Elec, Tant (CSR), Nonsolid, Elec, Tant (CL, CLR, CRL), Chip, Elec (CWR), Lead Mount, Elec, Alum (CE), Chassis Mount, Elec, Alum (CU, CUR), MOS
        - Inductor: Transformer, Coil
        - Connection: General, PCB Edge, IC Socket, Board with Plated Thru Holes, Other Connection, SMT Interconnect Assy
        若為主類別為 'None'，次類別也請給 'None'。"""
    )
    confidence_score: float = Field(description="AI 分類信心度 0.0 ~ 1.0")
    reason: str = Field(description="說明為何判定為該類別的簡短工程理由")

def classify_component_by_ai(part_number: str, description: str) -> tuple:
    """呼叫 AI 進行語意分析"""
    prompt = f"""
    你是一位資深的電子產品可靠度工程師 (DQA)。請根據以下元件的「料號 (Part Number)」與「規格描述 (Description)」，
    將其歸類到最符合的 Relex (MIL-HDBK-217 / Telcordia) 計算分類中。
    
    【待分類元件資訊】
    - 料號 (Part Number): {part_number}
    - 規格描述 (Description): {description}
    
    【注意事項】
    1. 請仔細辨識 Description 中的關鍵字（例如：RES, CAP, MLCC, IND, MOSFET, IC, DIODE, CONN, FB, Bead）。
    2. 如果判斷該項目屬於「機構件」或「非電子常規計算件」（例如貼紙、外殼、螺絲、包材），主類別與次類別皆直接回傳 "None"。
    """
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=RelexClassification,
                temperature=0.0, # 確保結果完全穩定、不隨機瞎猜
            ),
        )
        result = json.loads(response.text)
        return result['category'], result['subcategory'], result['confidence_score'], result['reason']
    except Exception as e:
        return "Error", str(e), 0.0, "API 呼叫失敗"

def process_bom_list(file_path: str, output_path: str):
    """讀取 Excel、處理分類、另存新檔的主程式"""
    # 讀取原始檔案
    df = pd.read_excel(file_path)
    
    # 🔍 請確認您 Excel 內實際的欄位名稱是否為這兩個 (大小寫需一致)
    pn_col = "PartNumber"
    desc_col = "Description"
    
    categories, subcategories, scores, reasons = [], [], [], []
    ai_cache = {} # 相同料號快取機制
    total_rows = len(df)
    
    print(f"\n====== 開始處理 ======")
    print(f"原始檔案：{file_path}")
    print(f"總計行數：{total_rows} 行\n")
    
    for index, row in df.iterrows():
        pn = str(row[pn_col]).strip() if pd.notna(row[pn_col]) else ""
        desc = str(row[desc_col]).strip() if pd.notna(row[desc_col]) else ""
        
        # 檢查快取，避免重複元件浪費 API 額度與時間
        if pn in ai_cache and pn != "":
            cat, subcat, score, reason = ai_cache[pn]
            reason_str = f"[快取複用] {reason}"
        else:
            cat, subcat, score, reason = classify_component_by_ai(pn, desc)
            if cat == "None":
                cat = ""
            if subcat == "None":
                subcat = ""
            if pn != "":
                ai_cache[pn] = (cat, subcat, score, reason)
            reason_str = reason
            print(f"[{index+1}/{total_rows}] AI 識別 -> PN: {pn} | 分類: {cat} -> {subcat}")
            
        categories.append(cat)
        subcategories.append(subcat)
        scores.append(score)
        reasons.append(reason_str)
        
    # 精準寫入原本 Excel 畫紅線的對應欄位 (如果原本有資料會被填滿/覆蓋)
    df['主分類'] = categories
    df['次分類'] = subcategories
    df['AI 信心度'] = scores
    df['AI 判定理由'] = reasons
    
    # 匯出成全新檔案
    df.to_excel(output_path, index=False)
    print(f"\n====== 處理完成 ======")
    print(f"新檔案已另存至：{output_path}")
    print(f"不重複料號總數：{len(ai_cache)} 種\n")

if __name__ == "__main__":
    # 檢查環境變數
    if not os.environ.get("GEMINI_API_KEY"):
        print("【錯誤】未偵測到 GEMINI_API_KEY 環境變數，請先設定您的通行碼。")
    else:
        # 隱藏 tkinter 的主視窗，只留下對話框
        root = tk.Tk()
        root.withdraw()
        
        # 1. 彈出視窗讓您選取要處理的原始 BOM 表
        print("請在彈出的視窗中，選擇您的原始 BOM Excel 檔案...")
        input_file = filedialog.askopenfilename(
            title="請選擇原始 BOM Excel 檔案",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        
        if input_file:
            # 2. 彈出視窗讓您決定「整理好的新檔案」要存去哪裡、叫什麼名字
            output_file = filedialog.asksaveasfilename(
                title="請指定整理好的新檔案儲存位置與檔名",
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile="Relex_BOM_Result.xlsx" # 預設產出的新檔名
            )
            
            if output_file:
                # 執行自動化分類與另存新檔
                process_bom_list(input_file, output_file)
            else:
                print("未指定儲存位置，程式結束。")
        else:
            print("未選取任何檔案，程式結束。")