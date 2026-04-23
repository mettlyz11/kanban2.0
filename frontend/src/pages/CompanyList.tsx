import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Search } from 'lucide-react'

interface Company {
  id: number
  name: string
  short_name: string
  legal_representative: string
  industry: string
  create_date: string
  address: string
  phone: string
  email: string
  website: string
  description: string
  last_updated: string
}

export function CompanyList() {
  const navigate = useNavigate()
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const [searchTerm, setSearchTerm] = useState('')

  useEffect(() => {
    fetchCompanies()
  }, [])

  const fetchCompanies = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/company-info/companies')
      const data = await res.json()
      if (data.success) {
        setCompanies(data.companies || [])
      }
    } catch (e) {
      console.error('获取公司列表失败:', e)
    } finally {
      setLoading(false)
    }
  }

  const filteredCompanies = companies.filter(company =>
    company.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    company.short_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    company.industry?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center">
        <div className="animate-spin w-10 h-10 border-4 border-[#0071e3] border-t-transparent rounded-full"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#f5f5f7]">
      {/* 顶部标题栏 */}
      <div className="sticky top-0 z-10 backdrop-blur-md bg-[#f5f5f7]/80 border-b border-[rgba(0,0,0,0.1)]/50">
        <div className="max-w-full px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center text-white">
                <Building2 className="w-6 h-6" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-[#1d1d1f]">公司列表</h1>
                <p className="text-sm text-[rgba(0,0,0,0.48)]">共 {companies.length} 家公司</p>
              </div>
            </div>

            {/* 搜索框 */}
            <div className="relative w-80">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[rgba(0,0,0,0.48)] w-5 h-5" />
              <input
                type="text"
                placeholder="搜索公司..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2.5 bg-white border-0 rounded-xl focus:outline-none focus:ring-2 focus:ring-[#0071e3] focus:bg-[#f5f5f7] transition-all"
              />
            </div>
          </div>
        </div>
      </div>

      {/* 公司列表 - 紧凑5列网格 */}
      <div className="max-w-full px-6 py-6">
        {filteredCompanies.length === 0 ? (
          <div className="text-center py-12 text-[rgba(0,0,0,0.48)]">
            <Building2 className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <p>未找到匹配的公司</p>
          </div>
        ) : (
          <div className="grid grid-cols-5 gap-3">
            {filteredCompanies.map(company => (
              <div
                key={company.id}
                onClick={() => navigate(`/company/${company.id}`)}
                className="bg-[#f5f5f7] rounded-lg p-3 border border-gray-100 hover:shadow-[0_4px_16px_rgba(0,0,0,0.12)] hover:border-blue-200 transition-all cursor-pointer group"
              >
                
                {/* 公司名称 */}
                <h3 className="text-xs font-semibold text-[#1d1d1f] text-center group-hover:text-[#0071e3] transition-colors truncate">
                  {company.name}
                </h3>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default CompanyList
