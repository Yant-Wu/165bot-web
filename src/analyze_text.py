import jieba

class TextAnalyzer:
    def analyze(self, text):
        if isinstance(text, str):
            word_count = len(list(jieba.cut(text)))
            if word_count == 0:
                return "輸入為空"
            elif word_count < 10:
                return f"文本字數較少，有 {word_count} 個字"
            else:
                return f"文本有 {word_count} 個字，字數較多"
        elif isinstance(text, list):
            results = []
            for t in text:
                word_count = len(list(jieba.cut(t)))
                if word_count == 0:
                    results.append("輸入為空")
                elif word_count < 10:
                    results.append(f"文本字數較少，有 {word_count} 個字")
                else:
                    results.append(f"文本有 {word_count} 個字，字數較多")
            return results
        else:
            return "輸入格式不正確，請輸入字符串或字符串列表"