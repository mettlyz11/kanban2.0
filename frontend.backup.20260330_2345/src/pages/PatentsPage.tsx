import React, { useState, useEffect } from 'react';
import { Card, Button, Table, Tag, Space, Typography, Statistic, Row, Col, Modal, Descriptions, message } from 'antd';
import { FileTextOutlined, DownloadOutlined, EyeOutlined, PlusOutlined, BarChartOutlined } from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;

const PatentsPage = () => {
  const [patents, setPatents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState(null);
  const [selectedPatent, setSelectedPatent] = useState(null);
  const [modalVisible, setModalVisible] = useState(false);

  // 优先级颜色映射
  const priorityColors = {
    'P0': 'red',
    'P1': 'orange',
    'P2': 'blue',
    'P3': 'green'
  };

  // 状态图标映射
  const statusColors = {
    '文档完成': 'success',
    '已提交': 'processing',
    '审查中': 'warning',
    '已授权': 'default'
  };

  useEffect(() => {
    fetchPatents();
    fetchStats();
  }, []);

  const fetchPatents = async () => {
    try {
      setLoading(true);
      const response = await fetch('/test-kanban/api/patents');
      const data = await response.json();
      
      if (data.success) {
        setPatents(data.data);
      } else {
        message.error('加载专利列表失败');
      }
    } catch (error) {
      console.error('获取专利数据失败:', error);
      message.error('网络错误');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await fetch('/test-kanban/api/patents/stats');
      const data = await response.json();
      
      if (data.success) {
        setStats(data.data);
      }
    } catch (error) {
      console.error('获取统计失败:', error);
    }
  };

  const showPatentDetail = (patent) => {
    setSelectedPatent(patent);
    setModalVisible(true);
  };

  const downloadDocument = (patent) => {
    // 实际应该从服务器下载文件
    message.info(`下载专利文档：${patent.title}`);
  };

  const columns = [
    {
      title: '优先级',
      dataIndex: 'priority',
      key: 'priority',
      width: 80,
      render: (priority) => (
        <Tag color={priorityColors[priority]}>{priority}</Tag>
      ),
      sorter: (a, b) => a.priority.localeCompare(b.priority)
    },
    {
      title: '专利名称',
      dataIndex: 'title',
      key: 'title',
      width: 400,
      render: (text, record) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.word_count}字 | {record.tech_field}
          </Text>
        </Space>
      )
    },
    {
      title: '类型',
      dataIndex: 'type',
      key: 'type',
      width: 100,
      render: (type) => <Tag>{type}</Tag>
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status) => (
        <Tag color={statusColors[status]}>{status}</Tag>
      )
    },
    {
      title: '发明人',
      dataIndex: 'inventors',
      key: 'inventors',
      width: 120,
      render: (inventors) => <Text>{inventors}</Text>
    },
    {
      title: '预计费用',
      dataIndex: 'estimated_cost',
      key: 'estimated_cost',
      width: 100,
      render: (cost) => <Text>¥{cost}万</Text>,
      sorter: (a, b) => a.estimated_cost - b.estimated_cost
    },
    {
      title: '操作',
      key: 'action',
      width: 150,
      render: (_, record) => (
        <Space size="small">
          <Button 
            type="link" 
            icon={<EyeOutlined />}
            onClick={() => showPatentDetail(record)}
          >
            详情
          </Button>
          <Button 
            type="link" 
            icon={<DownloadOutlined />}
            onClick={() => downloadDocument(record)}
          >
            下载
          </Button>
        </Space>
      )
    }
  ];

  return (
    <div style={{ padding: '24px', background: '#f0f2f5', minHeight: '100vh' }}>
      {/* 统计卡片 */}
      {stats && (
        <Card style={{ marginBottom: '24px' }}>
          <Row gutter={16}>
            <Col span={3}>
              <Statistic 
                title="总专利数" 
                value={stats.total_patents} 
                suffix="项"
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={3}>
              <Statistic 
                title="P0 核心" 
                value={stats.p0_count} 
                suffix="项"
                valueStyle={{ color: '#f5222d' }}
              />
            </Col>
            <Col span={3}>
              <Statistic 
                title="P1 重要" 
                value={stats.p1_count} 
                suffix="项"
                valueStyle={{ color: '#fa8c16' }}
              />
            </Col>
            <Col span={3}>
              <Statistic 
                title="P2 增强" 
                value={stats.p2_count} 
                suffix="项"
                valueStyle={{ color: '#1890ff' }}
              />
            </Col>
            <Col span={3}>
              <Statistic 
                title="P3 前沿" 
                value={stats.p3_count} 
                suffix="项"
                valueStyle={{ color: '#52c41a' }}
              />
            </Col>
            <Col span={3}>
              <Statistic 
                title="总字数" 
                value={stats.total_words / 10000} 
                suffix="万字"
                precision={1}
              />
            </Col>
            <Col span={3}>
              <Statistic 
                title="总预算" 
                value={stats.total_cost} 
                suffix="万元"
                precision={0}
                valueStyle={{ color: '#722ed1' }}
              />
            </Col>
          </Row>
        </Card>
      )}

      {/* 专利列表 */}
      <Card 
        title={
          <Space>
            <FileTextOutlined />
            T109 项目专利库（12 项）
          </Space>
        }
        extra={
          <Button type="primary" icon={<PlusOutlined />}>
            新增专利
          </Button>
        }
      >
        <Table 
          columns={columns}
          dataSource={patents}
          rowKey="id"
          loading={loading}
          pagination={{ pageSize: 20 }}
          scroll={{ x: 1200 }}
        />
      </Card>

      {/* 详情弹窗 */}
      <Modal
        title={selectedPatent?.title}
        visible={modalVisible}
        onCancel={() => setModalVisible(false)}
        footer={[
          <Button 
            key="download" 
            type="primary" 
            icon={<DownloadOutlined />}
            onClick={() => downloadDocument(selectedPatent)}
          >
            下载文档
          </Button>,
          <Button key="close" onClick={() => setModalVisible(false)}>
            关闭
          </Button>
        ]}
        width={900}
      >
        {selectedPatent && (
          <Descriptions column={1} bordered>
            <Descriptions.Item label="专利名称">{selectedPatent.title}</Descriptions.Item>
            <Descriptions.Item label="类型">{selectedPatent.type}</Descriptions.Item>
            <Descriptions.Item label="优先级">
              <Tag color={priorityColors[selectedPatent.priority]}>{selectedPatent.priority}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="状态">
              <Tag color={statusColors[selectedPatent.status]}>{selectedPatent.status}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="发明人">{selectedPatent.inventors}</Descriptions.Item>
            <Descriptions.Item label="申请人">{selectedPatent.applicant}</Descriptions.Item>
            <Descriptions.Item label="技术领域">{selectedPatent.tech_field}</Descriptions.Item>
            <Descriptions.Item label="核心创新点">
              <Paragraph>{selectedPatent.core_innovation}</Paragraph>
            </Descriptions.Item>
            <Descriptions.Item label="字数">{selectedPatent.word_count}字</Descriptions.Item>
            <Descriptions.Item label="预计费用">¥{selectedPatent.estimated_cost}万元</Descriptions.Item>
            <Descriptions.Item label="创建时间">{selectedPatent.created_at}</Descriptions.Item>
            <Descriptions.Item label="更新时间">{selectedPatent.updated_at}</Descriptions.Item>
          </Descriptions>
        )}
      </Modal>
    </div>
  );
};

export default PatentsPage;
