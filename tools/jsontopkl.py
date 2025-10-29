import json
import pickle
from sentence_transformers import SentenceTransformer
import os

# 設定檔案路徑
json_file_path = "QA.json"  # 這是你的 JSON 檔案
pkl_file_path = "embeddings_v3.pkl"   # 轉換後的 PKL 檔案

# 載入資料（假設資料是 JSON 格式）
def load_json_data(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

# 生成嵌入並將其與文本內容保存
def create_embeddings(data):
    # 使用 Hugging Face SentenceTransformer 來生成 1024 維度的嵌入
    model = SentenceTransformer('all-MiniLM-L6-v2')  # 這是 1024 維度模型

    # 將每個文本的內容轉換為嵌入
    embeddings = []
    for idx, document in enumerate(data):
        if document:  # 如果有內容
            embedding = model.encode([document])  # 生成嵌入
            embeddings.append((document, embedding[0]))  # 將嵌入與文本內容配對
            # 即時顯示當前處理的行數和進度
            print(f"處理第 {idx + 1} 行: {document[:30]}...")  # 顯示部分文本，避免過長
    return embeddings

# 保存嵌入資料到 PKL 檔案
def save_to_pkl(embeddings, file_path):
    with open(file_path, "wb") as f:
        pickle.dump(embeddings, f)

# 主程式：將 JSON 轉換為 PKL 檔案
def main():
    # 步驟 1：載入資料
    data = load_json_data(json_file_path)

    # 步驟 2：生成嵌入並與文本內容配對
    embeddings = create_embeddings(data)

    # 步驟 3：將嵌入資料保存為 PKL 檔案
    save_to_pkl(embeddings, pkl_file_path)
    print(f"資料已成功轉換並保存為 {pkl_file_path}")

if __name__ == "__main__":
    main()
