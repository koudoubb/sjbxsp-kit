# 翼狐 AI 后台：发布 / 更新视频笔记

只在用户明确要求发到后台时执行。默认交付物是 mp4 + 封面图，不上传。

后台：`https://ai-admin.yiihuu.com/#/note/noteManage`（内容管理 → 笔记管理）
接口域：`https://ai-admin-api.yiihuu.com`

## 登录（有图形验证码，不是纯账密）

1. 打开登录页。前端会先调 `GET /api/Login/getIsCode?admin_account=<账号>`，返回 `{"data":{"is_code":1}}` 表示该账号要验证码，页面才出现「验证码」输入框。
2. 用真实键盘输入账号密码（`page.keyboard.type`），点一下密码框等 `getIsCode` 返回。
3. 抓验证码图：取 `img` 中 `src.startsWith("data:image")` 的那一张（**内联 data URL，120×36**），base64 解码存盘，放大 4 倍再识别。
   - 坑：按"宽度取最后一个 img"会拿到站点 logo（350×56 的 GOYOR）。
4. 填入验证码 → 点「登 录」。
5. 判据：URL 跳到 `#/dashboard`，且 `POST /api/user/login` 返回 `status:true` + `access_token`。
   - 报「密码填写错误」= 账号密码本身错，和验证码无关；验证码错会单独提示。
   - 同一会话内验证码图不变，可复用已识别的字符。

## 新建一条视频笔记（store）

列表页点「添加笔记」→ 弹窗标题就是「添加笔记」。默认类型是**图片**，必须先切视频，切完才出现「视频封面」项。

1. 类型：找 `input[placeholder='请选择笔记类型']` 所在 `.el-select` 的 `__vue__`，`$emit("input", 1)` + `formVm.model.type = 1`。
2. 作者：先点「选择已有作者」radio（`author_type` 从 1 变 2），再展开作者下拉选人名。已知：`驴来` = `author_id: 5`。
3. 分类：「设计变现」= `category_id: 14`。
4. 文本四项用 native setter 同步 DOM 再写 model：笔记名称→`name`、作品来源→`from`、笔记标签→`tag`（多个用英文逗号）、笔记内容→`content`。
5. 上传封面 `#cover`（500×667）+ 视频 `#note_video`。
6. 发布状态 `status:1`、含 AI `is_ai_content:0`，保存。

## 笔记类型

- 视频 = `1`，图片 = `2`（`formVm.model.type`）。
- 分类「设计变现」= `14`。
- 作者固定「驴来」（`author_type:2`），来源按素材平台填（YouTube / 抖音 / 视频号）。
- 含 AI 生成内容：卡片是 HTML 排版 + 真实截图 → `0`（否）。
- 发布状态：`status:1` = 是。**编辑已有笔记时会莫名带出「是」，保存前必须回读 `.el-radio.is-checked` 确认**。

## 取表单实例

从 `.el-form` **向上**找 `__vue__.model`：

```js
const dlg = [...document.querySelectorAll(".el-dialog")].find((d) => d.offsetParent !== null);
const form = dlg.querySelector(".el-form");
let n = form, formVm = null;
while (n && n !== document.body) {
  if (n.__vue__ && n.__vue__.model) { formVm = n.__vue__; break; }
  n = n.parentElement;
}
```

从 `.el-dialog` 向上找会拿不到（弹窗是 form 的祖先）。

## 上传文件

- 封面 `#cover`（`.jpg,.png,.gif`，推荐 500×670）、视频 `#note_video`（`.mp4`）。
- `page.setInputFiles("css:.el-dialog #cover", 封面路径)`。

**关键：视频上传是「追加」不是「替换」。** 更新已有视频笔记时，传完新视频后 `model.path` 会变成 `[旧, 新]` 两条，直接保存就是一条挂两个视频的笔记。

正确做法：传完后从 `model.path` 里 filter 掉旧条目，只留新的，再保存：

```js
const keep = formVm.model.path.filter((p) => /v2/.test(p.name || p.url));
formVm.model.path = keep.length ? keep : formVm.model.path.slice(-1);
```

封面是单值，正常替换，不需要处理。

## 保存

`POST /api/note/update`，body 就是整个 `formVm.model`（含 `id`、`path`、`cover`、`status`、`view`、`sort` 等全部字段，原样带上即可）。

- 保存按钮：`.el-dialog__footer button.el-button--primary`（文本带全角空格，匹配不到「确定」）。
- 新建用 `POST /api/note/store`；详情 `GET /api/note/show?note_id=`；列表 `GET /api/note/list`。

**保存成功的判据**（三项同时成立）：`POST /api/note/store` 或 `/update` 返回 200 且响应体 `{"status":true}`；弹窗自动关闭；列表总数 +1（新建）或不变（编辑），新行「是否发布」开关为 `is-checked`。

**视频上传耗时**：32 MB 的 mp4 约 5 分钟，46 MB 也有过 10 秒内传完（同一天不同时段，取决于出口带宽）。所以**不要用固定等待时间判断**：轮询 `model.path.length > 0`，拿到 url 后再去源站校验字节数。上传完成的判据是 `model.path.length > 0`，**不是**页面提示文字——「请上传mp4格式，视频大小建议不超过300M」是固定说明，一直挂在那儿不代表失败。`path[0].name` 取的是本地文件名（如 `final`），只是展示名。

## 保存后验证（三步都要做）

1. 重新打开该笔记的编辑弹窗，读 `model`：
   - `path.length === 1` 且名字含新版标识
   - `cover` 是新文件名
   - `status === 1`，`.el-radio.is-checked` 文案是「是」
2. 列表回读：该行类型/分类/时间正确，「是否发布」开关为 ON；**总数不变**，确认没有误改/覆盖其它笔记（尤其同主题的图片笔记）。
3. 源站文件校验：
   - 静态资源域是 `img.ke.yiihuu.com`，`model` 里存的是 `/api/vueupload/...` 相对路径，前端拼 `https://img.ke.yiihuu.com///` + 路径。
   - `curl -I https://img.ke.yiihuu.com/api/vueupload/video/<...>.mp4` 的 `Content-Length` 必须等于本地 mp4 字节数。
   - 封面 `curl` 下来看尺寸是否 500×667、画面是否被裁。

## 不要做的事

- 不要为了"顺手"改动同主题的其它笔记（图文版与视频版往往是两条独立笔记）。
- 不要在用户没明确说"发布/上线"时把发布状态改成「是」。
- 不要用坐标点下拉选项（popper 收起时 rect 为 0×0，点击静默失败），用 `el.__vue__.$emit("input", value)` + `$forceUpdate()`，或对展开的 `.el-select-dropdown__item` 派发 `mousedown/mouseup/click` 三连。
- **不要往 `formVm.model` 里塞表单没绑定的键。** 手动加 `model.source = "微信"` 这类未知字段，`POST /api/note/store` 直接 **500 Server Error**（来源真正绑的是 `from`）。删掉多余键后同一份 payload 立刻 200。
  - 最常见的触发方式不是手动加，而是填表脚本的 key 写错：`const map = { source: "作品来源" }` 然后 `vm.model["source"] = 值`——DOM setter 已经正确写进 `from`，模型里又多出一个 `source`，保存必 500。
  - **保存前固定跑一遍清键**（对 `model` 的键与表单实际绑定字段做差集，或直接 `delete vm.model.source; delete vm.model.author; delete vm.model.avatar` 这类已知多余键），再点确定。
  - 判据：`POST /api/note/store` 返回 200 且 `{"status":true}`；只看到 `500 {"message":"Server Error"}` 就是这条。
- **不要用坐标点发布状态/含 AI 的 radio。** 弹窗滚到 1280px 高时 radio 落在视口外，`mouse.click` 静默失败，`is-checked` 不变但没报错。也点不动 `.el-radio__label`。唯一可靠的是拿 `.el-radio-group` 的 `__vue__` 调 `$emit("input", 1)`。
- **不要用坐标点列表里的「编辑」。** 1920 布局下按钮在 x≈1492，视口只有 1080 时点击无效。改在 `evaluate` 里 `btn.click()`。
