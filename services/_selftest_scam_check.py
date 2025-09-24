from services.scam_related_check import ScamRelatedChecker


def run_sample():
    text = (
        "我現在以檢察官的身份命令你，立刻去銀行把錢領出來，"
        "轉帳到這個帳戶78909876543456789。記住，行員問你的話，就說是家裡裝潢或是買車用的，"
        "絕對不能透露案情，否則就是洩密！我們會全程監控，不配合的話，我馬上就簽發拘票去逮捕你！"
    )
    checker = ScamRelatedChecker()
    print("is_related:", checker.is_related(text, history=[]))


if __name__ == "__main__":
    run_sample()
