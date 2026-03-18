/**
 * Mac Mini 监控数据接收模块
 * 用于接收本地Mac Mini推送的监控数据
 */

const express = require('express');
const router = express.Router();

// 存储最新的监控数据
let macMiniMetrics = {
  lastUpdate: null,
  serverName: 'Mac Mini M4 Pro (本地)',
  status: 'offline',
  metrics: null
};

const API_KEY = 'kanban_monitor_key_2024';

/**
 * POST /api/monitor/push
 * Mac Mini推送监控数据
 */
router.post('/push', (req, res) => {
  const { api_key, server_id, server_name, timestamp, metrics } = req.body;
  
  // 验证API密钥
  if (api_key !== API_KEY) {
    return res.status(401).json({ success: false, error: '无效的API密钥' });
  }
  
  // 更新监控数据
  macMiniMetrics = {
    lastUpdate: timestamp,
    serverName: server_name || 'Mac Mini',
    serverId: server_id,
    status: 'online',
    metrics: metrics
  };
  
  res.json({ success: true, message: '数据已接收' });
});

/**
 * GET /api/monitor/macmini
 * 获取Mac Mini监控数据
 */
router.get('/macmini', (req, res) => {
  // 检查数据是否过期（超过5分钟视为离线）
  if (macMiniMetrics.lastUpdate) {
    const lastUpdate = new Date(macMiniMetrics.lastUpdate);
    const now = new Date();
    const diffMinutes = (now - lastUpdate) / 1000 / 60;
    
    if (diffMinutes > 5) {
      macMiniMetrics.status = 'offline';
    }
  }
  
  res.json({
    success: true,
    data: macMiniMetrics
  });
});

/**
 * GET /api/monitor/servers
 * 获取所有服务器监控数据
 */
router.get('/servers', (req, res) => {
  const servers = [
    {
      id: 'aliyun',
      name: '阿里云服务器',
      location: '北京',
      status: 'online',
      type: 'cloud'
    },
    {
      id: 'macmini',
      name: macMiniMetrics.serverName,
      location: '本地',
      status: macMiniMetrics.status,
      lastUpdate: macMiniMetrics.lastUpdate,
      type: 'local'
    }
  ];
  
  res.json({
    success: true,
    data: servers
  });
});

module.exports = router;
