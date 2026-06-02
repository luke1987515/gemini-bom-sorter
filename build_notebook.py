import json

code_string = """import os
import time
import json
import pandas as pd
from typing import Literal
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
import getpass
from google.colab import files

# 1. 讓使用者在 Colab 中輸入 Gemini API Key
print("請輸入您的 Gemini API Key：")
api_key = getpass.getpass()
client = genai.Client(api_key=api_key)

# 2. 嚴格定義符合 Relex 標準的主類別與次類別限制
class RelexClassification(BaseModel):
    category: Literal[
        "Integrated Circuit", "Semiconductor", "Resistor", "Capacitor", 
        "Inductor", "Rotating Device", "Relay", "Switching Device", 
        "Connection", "Optical Device", "Mechanical Part", "Miscellaneous", "None"
    ] = Field(description="對應 Relex 的主類別 (Category)。若為機構件或不需計算的項目請給 'None'")
    
    subcategory: str = Field(
        description=\"\"\"對應 Relex 的次類別 (Subcategory)。必須嚴格符合指定名稱，例如：
        - Integrated Circuit: Logic, CGA or ASIC, PAL, PLA, Linear, Microprocessor, Memory, EEPROM, VHSIC/VLSI CMOS, GaAs Digital, Custom
        - Semiconductor: Diode, Microwave Diode, Thyristor, Transistor, Si FET, GaAs FET, Detector, Isolator, Emitter, Laser Diode
        - Resistor: Composition (RC, RCR), Film (RL, RLR, RN, RNR, RM), Film, Power (RD), Accurate, WW (RB, RBR), Lead Mount, WW Power (RW, RWR), Chassis Mount, WW Power (RE, RER), Thermistor (RTH), Network Film (RZ), Surface Mount, General
        - Capacitor: General Ceramic (CK, CKR), Temp Compensat, Ceramic (CC, CCR), Chip, Ceramic (CDR), Paper (CA, CP), Plastic (CFR), Mica (CM, CMR), Glass (CY, CYR), Solid, Elec, Tant (CSR), Nonsolid, Elec, Tant (CL, CLR, CRL), Chip, Elec (CWR), Lead Mount, Elec, Alum (CE), Chassis Mount, Elec, Alum (CU, CUR), MOS
        - Inductor: Transformer, Coil
        - Connection: General, PCB Edge, IC Socket, Board with Plated Thru Holes, Other Connection, SMT Interconnect Assy
        若為主類別為 'None'，次類別也請給 'None'。\"\"\"
    )
    confidence_score: float = Field(description="AI 分類信心度 0.0 ~ 1.0")
    reason: str = Field(description="說明為何判定為該類別的簡短工程理由")

def classify_component_by_ai(part_number: str, description: str) -> tuple:
    prompt = f\"\"\"
    你是一位資深的電子產品可靠度工程師 (DQA)。請根據以下元件的「料號 (Part Number)」與「規格描述 (Description)」，
    將其歸類到最符合的 Relex (MIL-HDBK-217 / Telcordia) 計算分類中。
    
    【待分類元件資訊】
    - 料號 (Part Number): {part_number}
    - 規格描述 (Description): {description}
    
    【注意事項】
    1. 請仔細辨識 Description 中的關鍵字（例如：RES, CAP, MLCC, IND, MOSFET, IC, DIODE, CONN, FB, Bead）。
    2. 如果判斷該項目屬於「機構件」或「非電子常規計算件」（例如貼紙、外殼、螺絲、包材），主類別與次類別皆直接回傳 "None"。
    \"\"\"
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=RelexClassification,
                    temperature=0.0, 
                ),
            )
            result = json.loads(response.text)
            return result['category'], result['subcategory'], result['confidence_score'], result['reason']
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                print(f"  [API 限制] 觸發頻率限制，等待 20 秒後自動重試 (第 {attempt+1} 次)...")
                import time
                time.sleep(20)
                continue
            return "Error", str(e), 0.0, "API 呼叫失敗"

def process_bom_in_colab():
    # 3. 在 Colab 中呼叫上傳檔案介面
    print("\\n請上傳您的原始 BOM Excel 檔案 (.xlsx)")
    uploaded = files.upload()
    
    if not uploaded:
        print("未上傳檔案，程式結束。")
        return
        
    input_file_name = list(uploaded.keys())[0]
    df = pd.read_excel(input_file_name)
    
    # 確保欄位名稱符合您的 Excel
    pn_col = "PartNumber"
    desc_col = "Description"
    
    categories, subcategories, scores, reasons = [], [], [], []
    ai_cache = {} 
    total_rows = len(df)
    
    print(f"\\n====== 開始處理 ======")
    print(f"總計行數：{total_rows} 行\\n")
    
    for index, row in df.iterrows():
        pn = str(row[pn_col]).strip() if pd.notna(row[pn_col]) else ""
        desc = str(row[desc_col]).strip() if pd.notna(row[desc_col]) else ""
        
        if pn in ai_cache and pn != "":
            cat, subcat, score, reason = ai_cache[pn]
            reason_str = f"[快取複用] {reason}"
        else:
            cat, subcat, score, reason = classify_component_by_ai(pn, desc)
            if cat == "None": cat = ""
            if subcat == "None": subcat = ""
            if pn != "":
                ai_cache[pn] = (cat, subcat, score, reason)
            reason_str = reason
            
        print(f"[{index+1}/{total_rows}] AI 識別 -> PN: {pn} | 分類: {cat} -> {subcat}")
        
        # 為了避免免費版 Gemini API 的頻率限制 (15 RPM)，每次呼叫後暫停 4 秒
        time.sleep(4)
            
        categories.append(cat)
        subcategories.append(subcat)
        scores.append(score)
        reasons.append(reason_str)
        
    df['主分類'] = categories
    df['次分類'] = subcategories
    df['AI 信心度'] = scores
    df['AI 判定理由'] = reasons
    
    output_file_name = "Relex_BOM_Result.xlsx"
    df.to_excel(output_file_name, index=False)
    
    print(f"\\n====== 處理完成 ======")
    print(f"不重複料號總數：{len(ai_cache)} 種")
    
    # 4. 在 Colab 中呼叫下載檔案介面
    print("\\n正在為您下載處理完成的檔案...")
    files.download(output_file_name)

process_bom_in_colab()
"""

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Gemini BOM Sorter\\n",
    "自動將硬體 BOM 表元件歸類至 Relex 可靠度預估標準。"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "!pip install pydantic google-genai pandas openpyxl"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    code_string
   ]
  }
 ],
 "metadata": {
  "colab": {
   "provenance": []
  },
  "kernelspec": {
   "display_name": "Python 3",
   "name": "python3"
  },
  "language_info": {
   "name": "python"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 0
}

with open("gemini-bom-sorter-colab.ipynb", "w", encoding="utf-8") as f:
    json.dump(notebook, f, ensure_ascii=False, indent=1)
