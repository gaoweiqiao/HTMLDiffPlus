#-*- coding: UTF-8 -*-
'''
这是根据C#的HTMLDiff库所写的Python版本，而且改良了可以识别汉字、标签、英文单词、数字和左右括号。
步骤1：把旧字符串分词到列表中，再把新字符串分词到列表中，然后把新字符串列表根据词进行索引。
步骤2：把位置索引存到列表中，因此格式相当于一个字典，字符串当做key，位置列表当做value。{string:[1,2,3]}
步骤3：将旧字符串列表的每个词在字典中查询，目的是取得最大长度的匹配。
步骤4：然后通过递归或循环，在最大匹配的左侧和右侧分别找到匹配，直到匹配找完。
步骤5：将新旧字符串列表和匹配进行比较。找到变动处。生成待加工的section列表
步骤6：将待加工的section依次进行加工。
步骤7：最后把加工后的section列表输出
'''
import re
from builtins import print
def isTag(string):
    regex = re.compile(r"<[^>]+>")
    return True if regex.match(string) else False
def isOpeningTag(string):
    regex = re.compile(r"<[^>/]+>")
    return True if regex.match(string) else False

class HTMLDiff:
    def __init__(self,oldText,newText):
        self.oldWords = self.__SplitWords(oldText)
        self.newWords = self.__SplitWords(newText)
        self.newWordsIndex = {}
        self.content = []
        self.tagWhiteList = re.compile(r"</?(?:table|tr|td|th|thead|tbody).*>")

    def __SplitWords(self,text):
        regex = re.compile(r"<[^>]+>|[\u4e00-\u9fa5]|[a-zA-Z\(\)]+|\d+|\s+")
        return regex.findall(text)

    def IndexNewWords(self):
        for i in range(0,self.newWords.__len__()):
            if self.newWords[i] not in self.newWordsIndex:
                self.newWordsIndex[self.newWords[i]] = []
            self.newWordsIndex[self.newWords[i]].append(i)

    def __findMaxMatch(self,startInOld, endInOld , startInNew , endInNew):
        '''
        找到最大匹配
        算法如下：
        每个旧词查找在新词字典的位置
        依次记录旧词在新词的每个位置及已经匹配的长度，记录最大的长度匹配的长度及在旧词列表的位置和在新词列表的位置，并把结果返回
        '''
        #记录每次循环前一次的单词位置(key)和截止上一次的匹配长度。{int:int}
        maxMatch = {"startInOld":0, "startInNew":0, "size":0}
        preRecord = {}
        for oldindex in range(startInOld, endInOld):
            record = {}
            if self.oldWords[oldindex] in self.newWordsIndex:
                for i in self.newWordsIndex[self.oldWords[oldindex]]:
                    if i < startInNew:
                        continue
                    if i >= endInNew:
                        break
                    record[i] = preRecord[i-1]+1 if (i-1) in preRecord else 1
                    if record[i] > maxMatch["size"]:
                        maxMatch["startInOld"] = oldindex - record[i] + 1
                        maxMatch["startInNew"] = i - record[i] + 1
                        maxMatch["size"] = record[i]
            preRecord = record
        return maxMatch if maxMatch["size"]>0 else None

    def findAllMatches(self,startInOld, endInOld , startInNew , endInNew):
        '''
        用栈+循环或者递归来取出所有匹配，并将所有匹配返回
        本例用栈+循环,这种方式需要在后面进行排序
        '''
        stack = []
        matches = []
        tmpBlock = {}
        block = {"startInOld": startInOld, "endInOld": endInOld, "startInNew": startInNew, "endInNew": endInNew}
        stack.append(block)
        while stack.__len__() > 0:
            block = stack.pop()

            match = self.__findMaxMatch(block["startInOld"], block["endInOld"], block["startInNew"], block["endInNew"])
            if match is not None:
                matches.append(match)
                matchOldEnd = match["startInOld"]+match["size"]
                matchNewEnd = match["startInNew"]+match["size"]
                if block["endInOld"] > matchOldEnd and block["endInNew"] > matchNewEnd:
                    tmpBlock["startInOld"] = matchOldEnd
                    tmpBlock["endInOld"] = block["endInOld"]
                    tmpBlock["startInNew"] = matchNewEnd
                    tmpBlock["endInNew"] = block["endInNew"]
                    stack.append(dict(tmpBlock))
                if block["startInOld"] < match["startInOld"] and block["startInNew"] < match["startInNew"]:
                    tmpBlock["startInOld"] = block["startInOld"]
                    tmpBlock["endInOld"] = match["startInOld"]
                    tmpBlock["startInNew"] = block["startInNew"]
                    tmpBlock["endInNew"] = match["startInNew"]
                    stack.append(dict(tmpBlock))
        return matches

    def diff(self):
        '''
        进行字符串diff的方法
        '''
        sections = []     #操作块
        posInOld = 0
        posInNew = 0
        self.IndexNewWords()
        matches = self.findAllMatches(0, self.oldWords.__len__(), 0, self.newWords.__len__())
        sortedmatches = sorted(matches, key=lambda d: d["startInOld"])
        #添加一个收尾标记，使最后一个match之后的文本也参与运算
        sortedmatches.append({"startInOld": self.oldWords.__len__(), "startInNew": self.newWords.__len__(), "size": 0})
        for match in sortedmatches:
            matchOldEnd = match["startInOld"]+match["size"]
            matchNewEnd = match["startInNew"]+match["size"]
            if posInOld == match["startInOld"]:
                if posInNew == match["startInNew"]:
                    pass
                else:
                    sections.append(("diffInsert", match["startInOld"], matchOldEnd, posInNew, match["startInNew"]))
            else:
                if posInNew == match["startInNew"]:
                    sections.append(("diffDelete", posInOld, match["startInOld"], match["startInNew"], matchNewEnd))
                else:
                    sections.append(("diffReplace", posInOld, match["startInOld"], posInNew, match["startInNew"]))
            sections.append(("none", match["startInOld"], matchOldEnd, match["startInNew"], matchNewEnd))
            posInOld = match["startInOld"]+match["size"]
            posInNew = match["startInNew"]+match["size"]
        #将sections中的数据依次进行处理
        for section in sections:
            if section[0] == "none":
                self.content.append("".join(self.newWords[section[3]:section[4]]))
            elif section[0] == "diffInsert":
                self.__wrapTag(section[0],self.newWords,section[3],section[4])
            elif section[0] == "diffDelete":
                self.__wrapTag(section[0],self.oldWords,section[1],section[2])
            elif section[0] == "diffReplace":
                self.__wrapTag("diffDelete",self.oldWords,section[1],section[2])
                self.__wrapTag("diffInsert",self.newWords,section[3],section[4])
            else:
                 print("error")
        content = "".join(self.content)
        return content

    def killTagOutOfWhiteList(self,tags):
        '''
        过滤标签白名单(self.tagWhiteList)外的标签
        '''
        for i in range(0,tags.__len__()):
            if self.tagWhiteList.match(tags[i]) is None:
                tags[i]=""

    def __wrapTag(self, cssClass, words, startpos, endpos):
        '''
        包裹标签，如果在self.__splitTagAndWords返回的结果中是文字则在文字两边包裹标签
        如果是标签列表，并且第一个标签是开始标签，则列表后面加一个<span>
        如果是标签列表，并且第一个标签是结束标签，则列表之前加</span>
        如果是标签列表，并且cssClass是diffDelete，说明是该标签在旧字符串上，而不再新字符串上，这是就把标签进行过滤
        最后把加工好的内容合并为字符串，放到self.content里待输出
        '''
        for isTagMode, words in self.__splitTagAndWords(words,startpos,endpos):
            if isTagMode :
                if isOpeningTag(words[0]):
                    if cssClass == "diffDelete":
                        self.killTagOutOfWhiteList(words)
                    words.append(r'<span class="{0}">'.format("diffTag"))
                    self.content.append("".join(words))
                else:
                    if cssClass == "diffDelete":
                        self.killTagOutOfWhiteList(words)
                    self.content.append(r'</span>'+("".join(words)))
            else:

                words.append(r'</span>')
                self.content.append(r'<span class="{0}">'.format(cssClass)+("".join(words)))

    def __splitTagAndWords(self, words, startpos, endpos):
        '''
        将待处理的区块中连续非标签内容和连续的标签内容分别输出出来
        '''
        isTagMode = isTag(words[startpos])
        tmp = startpos
        for pos in range(startpos, endpos):
            if isTag(words[pos]) == isTagMode:
                pass
            else:
                yield (isTagMode,words[tmp:pos])
                isTagMode = not isTagMode
                tmp = pos
        if tmp < endpos:
            yield (isTagMode,words[tmp:endpos])

if __name__ == "__main__":
    oldold = r'''<p><i>This is</i> some sample text to <strong>demonstrate</strong> the capability of the <strong>HTML diff tool</strong>.</p>
                                <p>It is based on the <b>Ruby</b> implementation found <a href='http://github.com/myobie/htmldiff'>here</a>. Note how the link has no tooltip</p>
                                <table cellpadding='0' cellspacing='0'>
                                <tr><td>Some sample text</td><td>Some sample value</td></tr>
                                <tr><td>Data 1 (this row will be removed)</td><td>Data 2</td></tr>
                                </table>
                                Here is a number 2 32'''

    newnew = r'''<p>This is some sample <strong>text to</strong> demonstrate the awesome capabilities of the <strong>HTML <u>diff</u> tool</strong>.</p><br/><br/>Extra spacing here that was not here before.
                                <p>It is <i>based</i> on the Ruby implementation found <a title='Cool tooltip' href='http://github.com/myobie/htmldiff'>here</a>. Note how the link has a tooltip now and the HTML diff algorithm has preserved formatting.</p>
                                <table cellpadding='0' cellspacing='0'>
                                <tr><td>Some sample <strong>bold text</strong></td><td>Some sample value</td></tr>
                                </table>
                                Here is a number 2 <sup>32</sup>'''
    hdiff = HTMLDiff(oldold,newnew)
    html = open("diffplus.html","wb+")
    body =  '''
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
    "http://www.w3.org/TR/html4/loose.dtd">
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
        <style>
            table {{
                border:1px solid #d9d9d9;
            }}
            td {{
                border:1px solid #d9d9d9;
                padding:3px;
            }}
            .diffTag{{
                background: yellow
            }}
            .diffInsert{{
                background: green;
                color : white;
            }}
            .diffDelete{{
                text-decoration: line-through;
                color : grey;
            }}
        </style>
    </head>
    <body>
        <div>{0}</div>
        <hr/>
        <div>{1}</div>
        <hr/>
        <div>{2}</div>
    <body>
</html>
            '''
    mydiff = body.format(oldold,newnew,hdiff.diff())
    html.write(mydiff.encode("utf-8"))
    html.close()