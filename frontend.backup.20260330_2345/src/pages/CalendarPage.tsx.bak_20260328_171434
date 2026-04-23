import React, { useState, useEffect } from 'react';
import { Card, Calendar, Badge, List, Tag, Typography, Spin, Alert, Space } from 'antd';
import { PhoneOutlined, EnvironmentOutlined } from '@ant-design/icons';

const { Title, Text } = Typography;

const CalendarPage = () => {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchEvents();
  }, []);

  const parseTime = (timeStr) => {
    if (!timeStr) return null;
    // 兼容两种格式：ISO 格式或 RFC2822 格式
    try {
      const date = new Date(timeStr);
      if (isNaN(date.getTime())) return null;
      return {
        date: date.toISOString().split('T')[0], // YYYY-MM-DD
        time: date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false }), // HH:MM
        dateTime: date
      };
    } catch (e) {
      console.error('时间解析失败:', timeStr, e);
      return null;
    }
  };

  const fetchEvents = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/calendar/events');
      const data = await response.json();
      
      if (data.success) {
        // 兼容两种返回格式：{data: [...]} 或 {events: [...]}
        const events = data.data || data.events || [];
        setEvents(events);
      } else {
        setError('加载日历事件失败');
      }
    } catch (err) {
      setError('网络错误');
      console.error('获取日历事件失败:', err);
    } finally {
      setLoading(false);
    }
  };

  const getListData = (value) => {
    const targetDateStr = value.format('YYYY-MM-DD');
    return events
      .map(event => {
        const startTime = parseTime(event.start_time);
        if (!startTime) return null;
        
        const eventDateStr = startTime.date;
        if (eventDateStr !== targetDateStr) return null;
        
        return {
          type: event.location?.includes('电话') ? 'phone' : 'meeting',
          title: event.title,
          time: startTime.time,
          location: event.location,
          description: event.description,
          originalEvent: event
        };
      })
      .filter(item => item !== null);
  };

  const dateCellRender = (value) => {
    const listData = getListData(value);
    
    if (listData.length === 0) {
      return null;
    }

    return (
      <div style={{ marginTop: 4 }}>
        {listData.map((item, index) => (
          <div key={index} style={{ marginBottom: 4 }}>
            <Badge 
              status={item.type === 'phone' ? 'processing' : 'success'}
              text={<span style={{ fontSize: 12 }}>{item.title}</span>}
            />
          </div>
        ))}
      </div>
    );
  };

  const selectedDateRender = (value) => {
    const listData = getListData(value);
    
    if (listData.length === 0) {
      return <div style={{ padding: 20, textAlign: 'center', color: '#999' }}>这一天还没有安排哦~</div>;
    }
    
    return (
      <List
        style={{ marginTop: 16 }}
        dataSource={listData}
        renderItem={item => (
          <List.Item>
            <List.Item.Meta
              title={
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  {item.type === 'phone' ? <PhoneOutlined /> : <EnvironmentOutlined />}
                  <Tag color={item.type === 'phone' ? 'blue' : 'green'}>
                    {item.time}
                  </Tag>
                  <Text strong>{item.title}</Text>
                </div>
              }
              description={
                <div>
                  <div>📍 {item.location || '未指定地点'}</div>
                  {item.description && <div style={{ marginTop: 4, color: '#666' }}>{item.description}</div>}
                </div>
              }
            />
          </List.Item>
        )}
      />
    );
  };

  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin size="large" tip="加载日历事件中..." />
      </div>
    );
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={2}>📅 日历视图</Title>
      
      {error && (
        <Alert
          message="错误"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: 24 }}
        />
      )}

      {events.length > 0 && (
        <Card title="即将到来的会议" style={{ marginBottom: 24 }}>
          <List
            dataSource={events
              .filter(e => {
                const startTime = parseTime(e.start_time);
                return startTime && startTime.dateTime > new Date();
              })
              .sort((a, b) => {
                const timeA = parseTime(a.start_time)?.dateTime?.getTime() || 0;
                const timeB = parseTime(b.start_time)?.dateTime?.getTime() || 0;
                return timeA - timeB;
              })
              .slice(0, 5)}
            renderItem={item => {
              const startTime = parseTime(item.start_time);
              const endTime = parseTime(item.end_time);
              const isPhone = item.location?.includes('电话');
              
              return (
                <List.Item>
                  <List.Item.Meta
                    title={
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        {isPhone ? <PhoneOutlined /> : <EnvironmentOutlined />}
                        <Tag color={isPhone ? 'blue' : 'green'}>
                          {isPhone ? '📞 电话会议' : '📍 现场会议'}
                        </Tag>
                        <Text strong>{item.title}</Text>
                      </div>
                    }
                    description={
                      <div>
                        <div>
                          ⏰ {startTime?.dateTime?.toLocaleString('zh-CN')} 
                          {endTime && ` - ${endTime.time}`}
                        </div>
                        <div>📍 {item.location || '未指定地点'}</div>
                      </div>
                    }
                  />
                </List.Item>
              );
            }}
          />
        </Card>
      )}

      <Card title="日历">
        <Calendar 
          fullscreen={false}
          dateCellRender={dateCellRender}
        />
        <div style={{ marginTop: 24 }}>
          <Title level={4}>📋 选中日期详情</Title>
          {selectedDateRender(new Date())}
        </div>
      </Card>
    </div>
  );
};

export default CalendarPage;
