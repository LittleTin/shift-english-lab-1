import copy,json,sys
from pathlib import Path

src,dst=map(Path,sys.argv[1:])
p=json.loads(src.read_text())
assert p['testId']=='test-02'
qs={q['number']:q for q in p['questions']}
gs={g['id']:g for g in p['groups']}
orig=copy.deepcopy(qs)
def q(n,**k):qs[n].update(k)
def o(n,letter,**k):next(x for x in qs[n]['options'] if x['id']==letter).update(k)
def g(i,k,old,new):
    x=gs[f't02-r-p6-{i:02d}']; assert x[k].count(old)==1,(i,k,old);x[k]=x[k].replace(old,new)
o(104,'D',text='mostly',zh='大多；主要地',whyZh='mostly 表示大部分或大致如此，不是選出三種設計中效率最高的最高級。')
o(106,'B',whyZh='前後逗號把這段隔開作為補充說明；標準英語的非限定關係子句不能用 that 引導。')
o(107,'D',text='lesser',zh='較小的；較次要的',whyZh='lesser 表示程度、規模或重要性較低，不能用來說瑕疵品的數量較少。')
q(114,prompt='The project leader said she had checked the revised schedule ____ before distributing it.',promptZh='專案負責人說，她在發出修訂後的時程表前，已先＿＿確認過該表。',evidence='she had checked the revised schedule herself')
q(117,prompt='Please save a local copy now; ____, you may have no copy to open when the network goes down.',promptZh='請現在存一份本機副本；＿＿，網路中斷時你可能連一份可開啟的副本都沒有。',evidence='Please save a local copy now; otherwise, you may have no copy to open when the network goes down.')
o(117,'C',text='in contrast',zh='相較之下',whyZh='前句建議保存副本，後句是不照做的可能後果，並非比較兩種情況。')
q(123,promptZh='只有在所有保護蓋＿＿就定位後，才能重新啟動設備。')
o(123,'C',zh='已；與 in place 搭配表示就定位')
q(127,promptZh='保留了一份黏著劑樣品，＿＿日後需要進一步分析。')
o(127,'C',zh='以備；以防萬一')
o(128,'B',whyZh='during 表示在某段時間內，不表示活動延後至特定日期。')
q(129,prompt='The purchase order requires that each carton ____ a packing list.',evidence='requires that each carton include a packing list')
o(133,'D',text='Leave customer names visible so the support team can identify the account.',zh='請保留可見的客戶姓名，讓支援團隊辨識帳戶。',whyZh='這會讓客戶姓名留在截圖中，與前文不得揭露客戶資訊的條件衝突。')
g(2,'passageZh','空托盤應裝回原先送達時所使用的紙箱。','空托盤應裝回送達時用的紙箱（英文關係子句的空格：[137]）。')
o(137,'B',zh='關係代名詞，指物')
g(3,'passageZh','所有志工上班時','所有志工在各自的班次開始時')
o(141,'A',whyZh='若第一班開始前就閉市，便與招募志工在市集開放時協助攤商及訪客的安排不合。')
g(4,'passageZh','每筆申請都必須 [143] ____ 一張顯示日期、金額及商家名稱的收據。','每筆申請都必須以一張列有日期、金額及商家名稱的收據來 [143] ____。')
g(4,'passageZh','提交費用報告','提交差旅費報銷單')
g(4,'passageZh','確認報告總額','確認報銷單總額')
o(145,'D',text='There is no need to explain the expense if a receipt is missing.',zh='若收據遺失，就不必說明該筆費用。',whyZh='前文明確說收據遺失時要填寫表單並說明該筆費用。')
g(4,'passage','Reports with missing details','Claims with missing details')
g(4,'passageZh','缺少細節的報告會退回更正，不會立即 [146] ____。','資料不全的報銷申請會退回更正，不會立即 [146] ____。')
q(146,explanationZh='報銷申請是付款的對象；returned 和 paid 是與 will be 搭配的兩個並列過去分詞。',evidence='Claims with missing details will be returned for correction rather than paid immediately.')
o(146,'D',zh='給付',whyZh=qs[146]['explanationZh'])
o(146,'C',whyZh='報銷申請是被支付的對象，不是主動付錢者。')
groups_corrected={'t02-r-p6-02','t02-r-p6-04'}
oldgroups={g['id']:g for g in json.loads(src.read_text())['groups']}
# Keep the original questions and relevant passage edition for existing attempts.
# The runtime must honor archivedPassage* before this candidate can be accepted.
for n,new in qs.items():
    before=orig[n]
    if new==before and new.get('groupId') not in groups_corrected:continue
    assert new['part'] in (5,6) and before['answer']==new['answer']
    saved=copy.deepcopy(before)
    gid=saved.get('groupId')
    if gid in groups_corrected:
        saved['archivedPassage']=oldgroups[gid]['passage']
        saved['archivedPassageZh']=oldgroups[gid]['passageZh']
    p.setdefault('legacyQuestions',[]).append(saved)
    new['id']+='-r2'
    new['revision']=1+(new.get('revision') or 1)
dst.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n')
print('Archived P5–6 updates:',sum(q!=orig[n] for n,q in qs.items()))
