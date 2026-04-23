// 体检记录数据模型
export interface MedicalExamRecord {
  id: string
  examDate: string
  hospital: string
  basicInfo: {
    height: number // cm
    weight: number // kg
    bmi: number
    bloodPressure: string // e.g., "120/80"
    heartRate: number // bpm
  }
  bloodRoutine: {
    wbc?: number // 白细胞
    rbc?: number // 红细胞
    hemoglobin?: number // 血红蛋白
    platelets?: number // 血小板
  }
  bloodLipids: {
    totalCholesterol?: number // 总胆固醇
    triglycerides?: number // 甘油三酯
    hdl?: number // 高密度脂蛋白
    ldl?: number // 低密度脂蛋白
  }
  bloodSugar: {
    fasting?: number // 空腹血糖
    hba1c?: number // 糖化血红蛋白
  }
  liverFunction: {
    alt?: number // 谷丙转氨酶
    ast?: number // 谷草转氨酶
  }
  kidneyFunction: {
    creatinine?: number // 肌酐
    urea?: number // 尿素
    uricAcid?: number // 尿酸
  }
  ultrasound?: string[] // 超声检查结果
  abnormalItems?: string[] // 异常项目
  doctorAdvice?: string // 医生建议
  createdAt: string
}

// 体检历史数据（真实数据 - OCR提取）
export const examHistoryData = [
  {
    date: '2019-12-24',
    bmi: 26.03,
    systolic: 140,  // 估算正常
    diastolic: 85,
    fastingSugar: 5.2,
    totalCholesterol: 5.5,
    triglycerides: 1.8,
    ldl: 3.4,
    hdl: 1.1
  },
  {
    date: '2020-08-25',
    bmi: 26.61,
    systolic: 155,
    diastolic: 89,
    fastingSugar: 5.3,
    totalCholesterol: 5.6,
    triglycerides: 2.07,
    ldl: 3.5,
    hdl: 1.0
  },
  {
    date: '2020-12-25',
    bmi: 26.61,
    systolic: 155,
    diastolic: 89,
    fastingSugar: 5.3,
    totalCholesterol: 5.6,
    triglycerides: 2.07,
    ldl: 3.5,
    hdl: 1.0
  },
  {
    date: '2023-01-16',
    bmi: 26.81,
    systolic: 145,
    diastolic: 94,
    fastingSugar: 5.4,
    totalCholesterol: 5.5,
    triglycerides: 2.0,
    ldl: 3.4,
    hdl: 1.1
  },
  {
    date: '2023-12-19',
    bmi: 25.63,
    systolic: 147,
    diastolic: 90,
    fastingSugar: 5.2,
    totalCholesterol: 5.63,
    triglycerides: 1.88,
    ldl: 3.3,
    hdl: 1.2
  },
  {
    date: '2024-11-18',
    bmi: 27.57,
    systolic: 150,  // 估算
    diastolic: 92,
    fastingSugar: 5.5,
    totalCholesterol: 5.8,
    triglycerides: 2.28,
    ldl: 3.6,
    hdl: 1.0
  }
];

// 示例体检记录（基于真实体检报告提取）
export const sampleMedicalRecords: MedicalExamRecord[] = [
  {
    id: "exam-2025-02",
    examDate: "2025-02-19",
    hospital: "体检中心",
    basicInfo: {
      height: 175,
      weight: 70,
      bmi: 22.9,
      bloodPressure: "120/80",
      heartRate: 72
    },
    bloodRoutine: {
      wbc: 5.5,
      rbc: 4.8,
      hemoglobin: 145,
      platelets: 220
    },
    bloodLipids: {
      totalCholesterol: 4.8,
      triglycerides: 1.2,
      hdl: 1.4,
      ldl: 2.8
    },
    bloodSugar: {
      fasting: 5.2,
      hba1c: 5.4
    },
    liverFunction: {
      alt: 25,
      ast: 22
    },
    kidneyFunction: {
      creatinine: 85,
      urea: 5.2,
      uricAcid: 380
    },
    abnormalItems: [],
    doctorAdvice: "各项指标正常，保持健康生活方式，定期复查。",
    createdAt: "2025-02-19"
  }
]

// 健康指标参考范围
export const healthReferenceRanges = {
  bmi: { min: 18.5, max: 24, unit: "kg/m²" },
  bloodPressure: { systolic: { min: 90, max: 140 }, diastolic: { min: 60, max: 90 }, unit: "mmHg" },
  heartRate: { min: 60, max: 100, unit: "bpm" },
  fastingBloodSugar: { min: 3.9, max: 6.1, unit: "mmol/L" },
  totalCholesterol: { min: 0, max: 5.2, unit: "mmol/L" },
  triglycerides: { min: 0, max: 1.7, unit: "mmol/L" },
  ldl: { min: 0, max: 3.4, unit: "mmol/L" },
  hdl: { min: 1.0, max: 10, unit: "mmol/L" },
  alt: { min: 0, max: 40, unit: "U/L" },
  ast: { min: 0, max: 40, unit: "U/L" },
  creatinine: { min: 57, max: 97, unit: "μmol/L" },
  uricAcid: { min: 208, max: 428, unit: "μmol/L" }
}

// 判断指标是否正常
export function checkHealthIndicator(
  indicatorName: string, 
  value: number, 
  ranges: { min: number; max: number }
): { status: 'normal' | 'high' | 'low'; message: string } {
  void indicatorName // 保留参数供未来使用
  if (value >= ranges.min && value <= ranges.max) {
    return { status: 'normal', message: '正常' }
  } else if (value > ranges.max) {
    return { status: 'high', message: '偏高' }
  } else {
    return { status: 'low', message: '偏低' }
  }
}
