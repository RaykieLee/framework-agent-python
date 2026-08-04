# 鍗囩骇鐢熸垚鐨勯」鐩?

褰撲綘鐢熸垚涓€涓」鐩悗锛屽畠灏卞睘浜?浣?浜?鈥斺€?浣犱細淇敼璺敱銆佹坊鍔犱笟鍔￠€昏緫銆佽皟鏁撮厤缃€備笌姝ゅ悓鏃讹紝鑴氭墜鏋舵湰韬篃鍦ㄦ寔缁敼杩涖€俙upgrade` 鍛戒护浼氭妸杩欎簺鏀硅繘**鍦ㄤ笉涓㈠け浣犲畾鍒跺唴瀹圭殑鍓嶆彁涓?*鍚堝苟杩涗綘鐜版湁鐨勯」鐩紝瀹冩墽琛岀殑鏄湡姝ｇ殑涓夋柟鍚堝苟(three-way merge),骞舵妸鍐茬獊鐣欑粰浣犵敤鏃ュ父鐨?git 宸ュ叿鏉ュ鐞嗐€?

- **鍦ㄩ」鐩唴閮ㄨ繍琛?*(`make upgrade`)銆?
- **涓嶄細闈欓粯瑕嗙洊浠讳綍鍐呭銆?* 鍙湁浣犳敼杩囩殑鏂囦欢浼氳淇濈暀锛涘彧鏈夎剼鎵嬫灦鏀硅繃鐨勬枃浠朵細琚洿鏂帮紱鍙屾柟閮芥敼杩囩殑鏂囦欢瑕佷箞鑷姩鍚堝苟锛岃涔堟爣璁颁负鍐茬獊浜ょ粰浣犺В鍐炽€?
- **濮嬬粓鍙挙閿€銆?* 鍗囩骇钀藉湪涓€涓笓闂ㄧ殑 git 鍒嗘敮涓婏紱浣犵殑鎻愪氦鍘嗗彶鍘熷皝涓嶅姩锛屼竴鏉″懡浠ゅ嵆鍙叏閮ㄥ洖閫€銆?

---

## 宸ヤ綔鍘熺悊(涓€寮犲浘璇存槑)

涓€娆″崌绾т細姣旇緝姣忎釜鏂囦欢鐨勪笁涓増鏈細

| 瑙掕壊   | 鍚箟                                                              |
| ------ | ----------------------------------------------------------------- |
| BASE   | 浣犵敓鎴愭椂鎵€鍩轰簬鐗堟湰鐨勮剼鎵嬫灦锛岀敤浣犲綋鍒濈殑绛旀娓叉煋鍑烘潵                |
| OURS   | 浣犲綋鍓嶇殑椤圭洰(浣犳鍦ㄤ娇鐢ㄣ€佸凡瀹氬埗鐨勪唬鐮?                          |
| THEIRS | 鐩爣鐗堟湰鐨勮剼鎵嬫灦锛屽悓鏍风敤浣犲綋鍒濈殑绛旀娓叉煋鍑烘潵                      |

涓や唤鑴氭墜鏋剁増鏈兘鐢?*浣犳渶鍒濈殑绛旀**鏉ユ覆鏌擄紝姝ｆ槸杩欎竴鐐逛繚璇佷簡鍚堝苟鐨勭簿纭€э細浠讳綍 BASE鈫扥URS 鐨勫樊寮傞兘纭疄鏄?浣?鐨勪慨鏀癸紝浠讳綍 BASE鈫扵HEIRS 鐨勫樊寮傞兘纭疄鏄?鑴氭墜鏋?鐨勫彉鏇淬€傚伐鍏蜂粠涓€涓皬娓呭崟鏂囦欢 `.fastapi-fullstack.json` 涓鍙栦綘鐨勭瓟妗堬紝璇ユ枃浠剁敱鐢熸垚鍣ㄥ啓鍏ユ瘡涓柊椤圭洰銆?

涓轰繚璇佽繖涓€鐐规垚绔嬶紝涓夋５鐩綍鏍戝湪姣旇緝涔嬪墠蹇呴』浠?鐩稿悓鏂瑰紡*鏍煎紡鍖?鈥斺€?鍚﹀垯鏍煎紡宸紓浼氳璇涓轰慨鏀广€傚崌绾ц繃绋嬩細鍦?BASE 鍜?THEIRS 涓婂鐜扮敓鎴愬櫒褰撳垵鍒涘缓浣犻」鐩椂鎵€鍋氱殑浜?`ruff check --fix`,鐒跺悗 `ruff format`,鍓嶇鍒欑敤 Prettier),鑰屼粠涓嶅 OURS 鎵ц鑷姩淇锛屽洜姝や綘鑷繁鐨勪唬鐮佸湪杩欎釜杩囩▼涓粷涓嶄細琚敼鍐欍€?

缁撴灉浼氬簲鐢ㄥ埌涓€涓柊鍒嗘敮 `template-upgrade/v<version>` 涓婏紝浣犲儚瀹℃煡浠讳綍鍏朵粬鍙樻洿涓€鏍峰幓瀹℃煡骞跺悎骞跺畠銆?

---

## 鍓嶇疆鏉′欢

- 椤圭洰蹇呴』鏄?*鍏惰嚜韬?git 浠撳簱鐨勬牴鐩綍**(`git rev-parse --show-toplevel` 鎸囧悜椤圭洰鐩綍)銆傚崌绾у悎骞剁殑鏄暣妫电洰褰曟爲锛屽鏋滀竴涓」鐩浜庢洿澶т粨搴撶殑鏌愪釜瀛愮洰褰曢噷锛屼袱杈圭殑璺緞鍚箟灏变笉涓€鑷达紝鏃犳硶瀵归綈銆傞亣鍒拌繖绉嶆儏鍐碉紝宸ュ叿浼氭嫆缁濊繍琛岋紝鑰屼笉鏄骇鍑洪敊璇殑鍚堝苟銆?
- **骞插噣鐨?git 宸ヤ綔鍖?*(鍏堟妸鏀瑰姩鎻愪氦鎴栨殏瀛樿捣鏉?銆傚惁鍒欏崌绾т細鎷掔粷杩愯锛屼互姝や繚璇佸缁堝彲鎾ら攢銆俙--dry-run` 鏄釜渚嬪锛氬畠鍙互鍦ㄨ剰宸ヤ綔鍖轰笂杩愯锛屼絾姣旇緝鐨勬槸浣犲凡鎻愪氦鐨?`HEAD`,鎵€浠ユ湭鎻愪氦鐨勬敼鍔ㄤ笉浼氬嚭鐜板湪棰勮涓?浣犱細鏀跺埌涓€鏉¤鍛?銆?
- 鑳借闂?**PyPI**(宸ュ叿浼氫粠宸插彂甯冪殑鍙戣鐗堜腑鎷夊彇鑴氭墜鏋剁増鏈?銆?
- 浣犵殑椤圭洰 **Makefile** 鎻愪緵浜?`make upgrade-dry-run` / `make upgrade` / `make upgrade-new-features` / `make upgrade-finalize`(鐢ㄨ繎鏈熺増鏈剼鎵嬫灦鐢熸垚鐨勯」鐩兘鑷甫杩欎簺)銆?
- **鍓嶇椤圭洰锛?* 鍏堝湪 `frontend/` 閲岃繍琛?`bun install`銆傚崌绾т細鐢ㄤ綘宸插畨瑁呯殑 Prettier 鏉ュ綊涓€鍖栨牸寮忥紝杩欐牱鑴氭墜鏋跺 `.ts/.tsx` 鏂囦欢鐨勬敼鍔ㄦ墠鑳藉共鍑€鍦板悎骞讹紱濡傛灉娌℃湁瀹冿紝鍓嶇鏂囦欢浼氶€€鍖栦负浠呯┖鐧界褰掍竴鍖栵紝鍙兘浜х敓铏氬亣宸紓銆?渚濊禆缂哄け鏃朵綘浼氭敹鍒拌鍛?鈥斺€?鍗囩骇浠嶄細缁х画杩愯銆?

---

## 鍦烘櫙 1 鈥斺€?椤圭洰甯︽湁娓呭崟鏂囦欢(甯歌鎯呭喌)

姣忎釜鐢ㄨ繎鏈熺増鏈剼鎵嬫灦鐢熸垚鐨勯」鐩兘鍖呭惈 `.fastapi-fullstack.json`銆傜敤 `ls .fastapi-fullstack.json` 妫€鏌ャ€傚鏋滃瓨鍦紝鎸変互涓嬫楠ゆ搷浣溿€?

### 1. 浠庡共鍑€鐘舵€佸紑濮?

````bash
cd my-project
git status            # 纭宸ヤ綔鍖烘槸骞插噣鐨?
git checkout -b before-upgrade   # 鍙€夛細涓€涓畨鍏ㄥ垎鏀?
````

### 2. 棰勮鍗囩骇(鍙€変絾鎺ㄨ崘)

````bash
make upgrade-dry-run             # 鎴栬€咃細fastapi-fullstack upgrade --dry-run
````

杩欎細鎵撳嵃涓€浠藉垎缁勬姤鍛婏紝涓斾笉鏀瑰姩浠讳綍鍐呭锛?

````
Upgrade plan: v0.2.10 鈫?v0.2.14

New files (3)                         鈫?鑴氭墜鏋舵柊澧炵殑鍔熻兘/鏂囦欢
New migrations (auto-added) (1)       鈫?鏂扮殑 Alembic 杩佺Щ
Changed migrations (review 鈥?these have probably already run) (1)
Auto-updates (template changed, you didn't) (12)
Auto-merged (both changed, merged cleanly) (2)
Kept your changes (template unchanged) (5)
Conflicts (need manual resolution) (1)
You deleted these (staying deleted) (2)  鈫?浣犲垹闄よ繃鐨勬枃浠讹紱鑴氭墜鏋朵粛鐒舵彁渚?
Your files (left untouched) (8)       鈫?鍙湁浣犲垱寤虹殑鏂囦欢

Manual steps after merge
  鈫?杩愯 `make db-upgrade`(鏂板浜嗚縼绉?銆?
  鈫?渚濊禆鍙樻洿鏃堕噸鏂拌繍琛?`uv lock` / `bun install`銆?
````

### 3. 搴旂敤

````bash
make upgrade                     # 鎴栬€咃細fastapi-fullstack upgrade
````

宸ュ叿浼氬垱寤哄垎鏀?`template-upgrade/v<version>`,搴旂敤姣忎竴澶勫畨鍏ㄥ彉鏇达紝娣诲姞鏂版枃浠跺拰杩佺Щ锛屽苟鎶婄湡姝ｇ殑鍐茬獊淇濈暀涓烘爣鍑嗙殑 git 鍐茬獊鏍囪銆傜粨鏉熸椂瀹冧細鎵撳嵃鍑虹‘鍒囩殑鎾ら攢鍛戒护銆?

濡傛灉鎯冲悓鏃堕噰绾充綘褰撳墠鐗堟湰涔嬪悗寮曞叆鐨?*鏂扮殑鍙€夊姛鑳?*(榛樿鍏抽棴 鈥斺€?鍗囩骇涓嶅簲鎮勬倓寮€鍚綘浠庢湭閫夋嫨杩囩殑鍔熻兘):

````bash
make upgrade-new-features    # 瀵规瘡涓柊鍔熻兘閫愪釜鎻愮ず Yes/No
````

### 4. 瑙ｅ喅鍐茬獊(濡傛灉鏈夌殑璇?

鍦ㄤ綘鐨?IDE 鐨勪笁鏂瑰悎骞剁紪杈戝櫒(PyCharm銆乂S Code 鎴?`git mergetool`)涓墦寮€鍐茬獊鏂囦欢銆傛爣璁颁細鏄剧ず浣犵殑鐗堟湰涓庤剼鎵嬫灦鐗堟湰鐨勫姣旓細

````python
<<<<<<< ours          # 浣犵殑鐗堟湰
API_TIMEOUT = 30
=======
API_TIMEOUT = 60      # 鑴氭墜鏋剁殑鐗堟湰
>>>>>>> theirs
````

瑙ｅ喅鍚庯紝鏆傚瓨杩欎簺鏂囦欢锛?

````bash
git add <resolved-files>
````

### 5. 鏀跺熬

````bash
make upgrade-finalize            # 鎴栬€咃細fastapi-fullstack upgrade finalize
````

杩欎細妫€鏌ョ洰褰曟爲宸叉棤鍐茬獊锛屽苟**鎶婃竻鍗曟枃浠?*鍗囩骇鍒版柊鐗堟湰銆?鍙杩樻湁鍐茬獊瀹冨氨鎷掔粷杩愯 鈥斺€?杩欓亾瀹夊叏缃戠‘淇濇竻鍗曚笉浼氳皫鎶ヤ綘鐨勭増鏈€?

### 6. 杩愯鍚庣画姝ラ骞跺悎骞?

````bash
uv lock            # 鍚庣渚濊禆鍙樻洿鏃?
bun install        # 鍓嶇渚濊禆鍙樻洿鏃?鍦?frontend/ 閲岃繍琛?
make db-upgrade    # 鏂板浜嗚縼绉绘椂
make test          # 纭娌℃湁鐮村潖浠讳綍涓滆タ
````

鐒跺悗鎶?`template-upgrade/v<version>` 鍍忎换浣?PR 涓€鏍峰悎骞惰繘浣犵殑涓诲垎鏀€?

### 闅忔椂鎾ら攢 {#sui-shi-che-xiao}

````bash
git checkout -f <your-branch> \
  && git branch -D template-upgrade/v<version> \
  && rm -f .fastapi-fullstack.json.pending
````

杩欓噷鐨?`-f` 涓嶆槸鍙€夌殑銆傚啿绐佹湭瑙ｅ喅鏃讹紝鏅€氱殑 `git checkout` 浼氱洿鎺ユ嫆缁濓紱鑰屼竴鏃﹁В鍐筹紝瀹冨弽鑰屼細鎶婃殏瀛樼殑鍗囩骇*甯﹀埌浣犺嚜宸辩殑鍒嗘敮涓?,鑰屼笉鏄涪寮冨畠 鈥斺€?缁撴灉鏄綘鎶婃暣涓崌绾ф殏瀛樺湪浜?`main` 涓婏紝鑰屽垎鏀嵈琚垹浜嗐€俙upgrade` 缁撴潫鏃朵細鎵撳嵃杩欐潯纭垏鐨勫懡浠わ紝鐢ㄩ偅鏉″氨濂姐€?

---

## 鍦烘櫙 2 鈥斺€?娌℃湁娓呭崟鏂囦欢鐨勬棫椤圭洰

鍦ㄦ竻鍗曞姛鑳藉嚭鐜颁箣鍓嶇敓鎴愮殑椤圭洰娌℃湁 `.fastapi-fullstack.json`(`ls .fastapi-fullstack.json` 鈫?鏈壘鍒?銆傚伐鍏锋棤娉曞緱鐭ュ畠浠綋鍒濇槸鍩轰簬浠€涔堢瓟妗堢敓鎴愮殑锛屾墍浠ヤ綘寰楀厛鍒涘缓涓€涓竻鍗曟枃浠讹紝瀹℃煡瀹冿紝鐒跺悗鍍忓満鏅?1 閭ｆ牱鍗囩骇銆?

### 1. 閲嶅缓涓€涓€欓€夋竻鍗?

````bash
cd my-legacy-project
fastapi-fullstack upgrade recover
````

杩欎細妫€鏌ヤ綘椤圭洰鐨勬枃浠跺竷灞€鏉ユ帹鏂摢浜涘姛鑳芥槸寮€鍚殑锛屼粠 README 椤佃剼璇诲彇鐗堟湰鍙凤紝骞跺啓鍑轰竴涓?*鍊欓€?*鏂囦欢 `.fastapi-fullstack.json.candidate`銆傚畠缁濅笉浼氱浣犵殑浠ｇ爜锛屼篃缁濅笉鍐欏叆鐪熸鐨勬竻鍗?鈥斺€?鎭㈠鏄敖鍔涜€屼负鐨勶細

- 瀹冭兘鍙潬鍦版娴?*甯冨皵绫诲瀷鐨勫姛鑳藉紑鍏?*(RAG 寮€/鍏炽€佹槸鍚︽湁鍓嶇銆佷换鍔￠槦鍒楅€変簡鍝釜銆丄I 妗嗘灦閫変簡鍝釜 绛夌瓑)銆?
- 瀹?*鏃犳硶**鎭㈠閭ｄ簺涓嶇暀缁撴瀯鎬х棔杩圭殑*鍙栧€?璁剧疆 鈥斺€?`db_pool_size`銆乣timezone`銆乣author_name`銆乣project_description`銆佺鍙ｃ€丩LM/鍚戦噺搴撶殑閫夋嫨绛夌瓑銆傝繖浜涗細鍦ㄤ竴鏉¤鍛婁腑鍒楀嚭锛岀暀缁欎綘鎵嬪姩濉啓銆?

### 2. 瀹℃煡骞舵彁鍗囨竻鍗?

鎵撳紑 `.fastapi-fullstack.json.candidate`,濡傛灉妫€娴嬪埌鐨?`package_version` 涓嶅灏辨敼姝ｅ畠锛屽苟琛ヤ笂璀﹀憡涓爣璁扮殑浠讳綍鍙栧€?鍦?`context` 瀵硅薄鍐?銆俢ontext 瓒婂噯纭紝鍗囩骇涓殑鍣０灏辫秺灏?context 涓嶅噯纭細璁╂湰娌℃敼杩囩殑鏂囦欢鏄惧緱"琚敼杩? 鈥斺€?瀹夊叏锛屼絾浼氬緢鍚?銆?

鐪嬭捣鏉ユ病闂鍚庯紝鎶婂畠鎻愬崌涓烘寮忔竻鍗曞苟鎻愪氦锛?

````bash
mv .fastapi-fullstack.json.candidate .fastapi-fullstack.json
git add .fastapi-fullstack.json && git commit -m "chore: add upgrade manifest"
````

### 3. 鍍忓満鏅?1 閭ｆ牱鍗囩骇

鑷虫浣犵殑椤圭洰灏辫兘鑷垜鎻忚堪浜?鈥斺€?鎸?*鍦烘櫙 1** 鎿嶄綔(`make upgrade` 鈫?瑙ｅ喅鍐茬獊 鈫?`make upgrade-finalize`)銆備互鍚庢瘡娆″崌绾ч兘鏄竴娆″共鍑€銆佸熀浜庢竻鍗曠殑杩愯銆?

## 理解报告

| 部分 | 含义 | 操作 |
|---|---|---|
| **新文件** | 模板新增了你没有的文件。 | 已添加。 |
| **新迁移** | 新的 Alembic 迁移文件。 | 已添加（仅追加，安全）。运行 make db-upgrade。 |
| **已更改的迁移** | 模板重写了你已有的迁移文件。 | 已更新——但不会再执行，请对照实际数据库 schema 检查。 |
| **自动更新** | 模板更改了你未修改的文件。 | 更新为模板版本。 |
| **自动合并** | 双方都更改了文件，但改动不重叠。 | 由 git 干净合并。 |
| **保留你的更改** | 你更改了模板未修改的文件。 | 保留你的版本。 |
| **已趋同** | 你和模板做了相同更改。 | 无需操作。 |
| **冲突** | 双方修改了相同行，或以不同方式添加了相同文件。 | 保留冲突标记供你处理。 |
| **你的文件** | 仅由你创建的文件。 | 从未触碰。 |
| **模板删除** | 模板删除了你未修改的文件。 | 建议删除。 |
| **你已删除** | 你删除了模板仍提供且未更改的文件。 | 保持删除——无需操作。 |
| **其他更改** | 上表未涵盖的任何内容。 | 请审查分支。应很少见——如果出现值得报告。 |

---

## 永远不会被触碰的内容

合并始终跳过以下内容——它们从不被读取、写入或合并：

- **密钥**：.env、.env.*——但已提交的示例文件（.env.example、.env.sample、.env.template）除外，它们会正常合并，以便版本新增的设置能到达你手中
- **锁定文件**：uv.lock、package-lock.json、un.lock、un.lockb（如果依赖有变化，升级后重新生成）
- .git/、
ode_modules/、.venv/、构建产物、__pycache__/、缓存
- .gitattributes 和 git 子模块
- 系统垃圾文件：.DS_Store、Thumbs.db
- **符号链接**，包括你的和模板的。被跟踪的符号链接永远不会被删除或重新暂存，模板也无法提供符号链接。一个值得注意的例外：一个*未跟踪*的符号链接恰好在升级要写入文件的位置时，会被该文件替代（不会通过链接写入——但链接会消失）。如果你需要它，请先将其移开。
- 清单本身（.fastapi-fullstack.json）——仅由 upgrade finalize 更新。其临时文件（.pending、.candidate）在新项目中已被 gitignore

Alembic 迁移**不被排除**——它们像其他文件一样合并。它们拥有自己的报告部分，因为故障模式不同：**新**迁移自动添加（仅追加，安全），你自己的迁移保留为仅客户端文件，而模板**更改**的迁移会在*已更改的迁移*下单独列出。

请仔细阅读该部分。你已有的迁移几乎肯定已针对你的数据库运行过，而 alembic 依赖修订 ID——因此重写的主体不会重新执行，文件会悄然停止描述它实际产生的 schema。升级仍会应用更改（它在分支上，并且某个版本有时确实会修复一个确实有问题的迁移），但你需要决定：保留它，还是在合并前执行 git checkout HEAD~ -- <file>。

---

## 清单 —— .fastapi-fullstack.json

写入每个生成的项目。它记录了生成器版本以及项目构建所依据的完整答案集，因此升级是可重现的。它**不包含任何密钥**（密钥形式的值在写入前会被剥离），因此提交它是安全的——并且你应该提交它。

```json
{
  "template": ""https://github.com/vstorm-co/full-stack-ai-agent-template"",
  "template_ref": ""0.2.14"",
  "package_version": ""0.2.14"",
  "generated_at": ""2026-07-01T10:00:00Z"",
  "context_hash": ""sha256:..."",
  "context": { "project_name": ""..."", "enable_rag": false, ""..."": ""..."" }
}
```

upgrade finalize 是**唯一**会更新 package_version 的操作——并且只在干净、无冲突的解决之后——因此清单永远不会声称你未完全合并的版本。

---

## 命令参考

```bash
# 在项目内（Makefile 封装）
make upgrade-dry-run               # 预览报告，不做任何更改
make upgrade                       # 执行升级
make upgrade-new-features          # 升级 + 选择加入新增功能
make upgrade-finalize              # 解决后更新清单

# 额外/一次性标志通过 ARGS 传入普通 upgrade 目标：
make upgrade ARGS=--to=0.3.0

# 底层 CLI（从任何位置运行，使用 --path，或从项目目录运行）
fastapi-fullstack upgrade [--path DIR] [--to VERSION] [--dry-run] [--with-new-features] [--force]
fastapi-fullstack upgrade finalize [--path DIR]
fastapi-fullstack upgrade recover  [--path DIR]
```

| 标志 | 效果 |
|---|---|
| --dry-run | 打印报告，不做任何更改。 |
| --to VERSION | 升级到特定版本而非最新版本。 |
| --with-new-features | 提示是否采用自你的版本以来新增的可选功能（默认关闭）。 |
| --force | 即使工作区不干净也强制运行。 |

内容 diff 无法识别某个文件在版本间被**重命名/移动**,也无法识别某个 cookiecutter **变量被重命名** —— 它会把这些读成无关的删除 + 添加，从而丢失客户端的改动。把这些结构性事实记录到 `UPGRADES.yaml`(仓库根目录),每个发行版一个块：

```yaml
- version: "0.2.15"
  renames:                       # 文件/目录移动 —— 末尾 "/" 表示整个目录
    - from: "backend/app/core/config.py"
      to:   "backend/app/core/settings.py"
    - from: "backend/app/rag/"
      to:   "backend/app/knowledge/"
## 给脚手架维护者 —— `UPGRADES.yaml`
  variable_renames:              # 各版本间被重命名的 cookiecutter context 键
    - from: "use_pgvector"
      to:   "vector_store"
      value_map: { "true": "pgvector" }
  removed:                       # 脚手架有意删除的文件
    - "backend/app/legacy_auth.py"
  breaking:                      # 在升级报告中呈现
    - "JWT secret env var renamed SECRET_KEY → AUTH_SECRET_KEY."
  manual_steps:                  # 工具无法替客户端完成的事
    - "Run `alembic upgrade head` (new billing tables)."
```

- **renames** 在合并前把移动的文件在 BASE/OURS 之间对齐，使客户端的改动跟随文件去到新路径，而不是丢失。
- **variable_renames** 在 context 调和期间把旧答案映射到新键。
- **removed** 记录有意删除的文件，在报告中显示，让用户知道这个消失是故意的。
- **breaking** + **manual_steps** 会在升级范围内的每个版本间汇总，并在报告中显示。

### 自动记录重命名

你不必手写 `renames` 块。发行时运行：

```bash
uv run python scripts/record_renames.py            # 检测移动并写入
uv run python scripts/record_renames.py --dry-run  # 仅打印建议的块
```

它会拉取上一个已发布的脚手架版本，按内容相似度把删除和添加配对，并把新的移动写入当前版本下的 `UPGRADES.yaml`。**审查一下 diff** —— 相似度匹配偶尔会配错移动，而一个错误的 rename 会丢失客户端改动。然后手动添加任何 `breaking` / `manual_steps` / `variable_renames` —— 这些描述的是 diff 无法推断的意图。

一个 CI 守卫(`scripts/check_rename_coverage.py`,由 `.github/workflows/rename-guard.yml` 运行)会 diff 相邻的两个发行版，如果某个疑似文件移动没有对应的 `renames` 条目(或显式豁免),就**让构建失败** —— 这样被遗漏的 rename 就无法悄悄发布。失败时它会打印一个可直接粘贴的块。

---

## 疑难排查

**"No `.fastapi-fullstack.json` found — run recovery first."**
你的项目早于清单功能 —— 按**场景 2** 操作。

**"Working tree has uncommitted changes."**
先提交或暂存。升级要求干净的工作区以保持可撤销。

**"… is not the root of its git repository."**
你的项目处在一个更大仓库的子目录里。合并比较的是整棵目录树，除非项目本身就是仓库根目录，否则两边对路径含义的理解不一致 —— 于是工具宁可拒绝，也不产出错误的合并。给这个项目一个独立的仓库。

**"frontend formatting was uneven."**
某个格式化工具只跑在了三棵树中的部分树上而非全部，于是它名下的文件会显得被改动过而实际没有。已提交的 `frontend/node_modules` 没问题 —— 那个安装会被就地使用。出问题的是安装里没有 `.bin/prettier`,或者某个拒绝符号链接的平台。在 `frontend/` 里运行 `bun install` 再重试。

**"Unresolved merge conflicts remain" when finalizing.**
解决剩余冲突并 `git add` 它们，然后再运行一次 `upgrade finalize`。

**"Kept your changes" 里有很多我并没改过的文件。**
你的清单 context 没有完美匹配项目当初的生成方式(场景 2 恢复后常见)。它是安全的 —— 什么都不会被覆盖 —— 但能自动应用的脚手架更新更少。改善清单的 `context` 可以缓解。

**升级后 README 的版本页脚仍显示旧版本。**
这是预期的。渲染时有意复用原始戳记，以免在合并期间产生冲突；只有清单会在 `finalize` 时更新版本号。如果你依赖那个页脚，手动更新它。

**我想把整个升级丢掉重来。**
`git checkout -f <your-branch> && git branch -D template-upgrade/v<version> && rm -f
.fastapi-fullstack.json.pending`。保留 `-f` 和 `rm` —— 见[随时撤销](#sui-shi-che-xiao)。
