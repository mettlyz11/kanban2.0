# -*- coding: utf-8 -*-
import sys
sys.path.insert(0,'/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection
execution_log = '''本次任务已执行了作者池构建、邮件草稿生成、附件落库与审核材料整理，但未将任务标记为 completed。首先按要求尝试检索“2026 年 MIT 材料系在 Nature Materials/Science Advances 发表的 AI 材料论文”，先后使用公开网页抓取与 Crossref API 检索。过程中遇到两个问题：其一，web_fetch 对目标站点访问被网关拦截，返回 private/internal/special-use IP address；其二，Crossref 对这类复合条件检索（机构+院系+年份+期刊+AI材料）结果噪声较大，无法可靠精确定位 10 位目标通讯作者及邮箱。为避免虚构论文与错误外联对象，我转而基于 MIT DMSE 公开师资与已知研究方向，整理了 10 位潜在合作作者池，生成每位作者的个性化合作意向邮件草稿，另外输出了我方代表性论文/合作方向建议文件，以及邮件发送清单与跟踪表。所有产出已保存至 output/task-2116，并已逐个插入 attachments 附件表，共 27 个文件。当前阶段建议进入人工审核：一是确认发送人身份、正式署名和邮箱；二是决定是否在首轮邮件中加入访问北航邀请；三是补齐并核验每位作者对应的 2026 目标论文、通讯作者身份、邮箱与更强个性化内容。由于核心事实检索仍待人工复核，因此本次仅适合保持 pending/review_needed，不宜直接 completed。'''
result_summary = '''已完成可审核版本的对外联络准备材料：构建了 10 位 MIT 材料系潜在合作作者池（待核验版），生成 10 封个性化合作意向邮件草稿，整理了“我方代表性论文与合作方向建议”以及“邮件发送清单与跟踪表”，并将全部文件写入 output/task-2116 且插入附件表。由于公开检索受限，尚未可靠确认“2026 年 Nature Materials/Science Advances 的 AI 材料论文”及其通讯作者对应关系，因此当前更适合进入人工审核与补证阶段，而不是直接发送。'''
task_summary = '已产出 MIT 材料系 10 位潜在合作对象清单、10 封个性化邮件草稿、合作方向建议及跟踪表，并完成附件入库；因目标论文与通讯作者身份仍需核验，建议保持 review_needed/pending，待确认署名、邀请口径和目标论文后再发送。'
conn = get_db_connection()
c = conn.cursor()
c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('pending', execution_log, result_summary, task_summary, 2116))
conn.commit()
conn.close()
# print('数据库已更新为 pending')
