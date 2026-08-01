import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../api'
import { useDialog } from '../components/DialogContext'
import { keys, useShopItems, useUser } from '../queries'
import { getUserId, isTeacher } from '../utils/auth'
import '../styles/shared-ui.css'
import './Shop.css'

const TABS = [
  { key: 'all', label: 'All' },
  { key: 'avatar_base', label: 'Avatars' },
  { key: 'avatar_accessory', label: 'Accessories' },
  { key: 'theme', label: 'Themes' },
]

const ITEM_TYPE_LABELS = {
  avatar_base: 'Avatar',
  avatar_accessory: 'Accessory',
  theme: 'Theme',
}

function Shop() {
  const userId = getUserId()
  const queryClient = useQueryClient()
  const { alert } = useDialog()
  const [itemType, setItemType] = useState('all')
  const [purchasingId, setPurchasingId] = useState(null)

  const { data: user = null } = useUser(userId)
  const { data: items = null, isLoading } = useShopItems()

  // Teachers don't earn/spend points; keep them off this student-only page,
  // same guard as Points.jsx.
  if (isTeacher()) {
    return <Navigate to="/dashboard" replace />
  }

  async function handlePurchase(item) {
    setPurchasingId(item.item_id)
    try {
      const { data } = await api.post(`/shop/items/${item.item_id}/purchase`)
      queryClient.setQueryData(keys.shopItems(), (prev) =>
        (prev || []).map((i) => (i.item_id === item.item_id ? { ...i, owned: true, equipped: false } : i))
      )
      queryClient.setQueryData(keys.user(userId), (prevUser) =>
        prevUser ? { ...prevUser, total_points: data.total_points } : prevUser
      )
      queryClient.invalidateQueries({ queryKey: ['points'] })
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not complete this purchase.')
    } finally {
      setPurchasingId(null)
    }
  }

  const loading = isLoading || items === null
  const rows = loading
    ? []
    : items.filter((i) => i.item_type !== 'badge' && (itemType === 'all' || i.item_type === itemType))
  const balance = user?.total_points ?? 0

  return (
    <section className="shop-page">
      <h1 className="admin-page-h1">Shop</h1>

      <div className="shop-balance">
        <span className="shop-balance-value">{balance}</span>
        <span className="shop-balance-label">points available</span>
      </div>

      <div role="tablist" aria-label="Shop category" className="admin-filter-chips">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={itemType === tab.key}
            className={`admin-chip${itemType === tab.key ? ' active' : ''}`}
            onClick={() => setItemType(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {loading && <p className="admin-empty-card">Loading shop items…</p>}
      {!loading && rows.length === 0 && <p className="admin-empty-card">No items to show.</p>}
      {!loading && rows.length > 0 && (
        <div className="shop-grid">
          {rows.map((item) => {
            const canAfford = balance >= item.cost
            return (
              <div className="shop-card" key={item.item_id}>
                <div className="shop-card-image">
                  <img src={item.image_url} alt="" />
                </div>
                <div className="shop-card-header">
                  <span className="shop-card-title">{item.name}</span>
                  <span className="shop-card-type">{ITEM_TYPE_LABELS[item.item_type] || item.item_type}</span>
                </div>
                {item.description && <p className="shop-card-description">{item.description}</p>}
                <div className="shop-card-footer">
                  <span className="shop-card-cost">{item.cost} pts</span>
                  {item.owned ? (
                    <span className="shop-card-status shop-card-status-owned">Owned</span>
                  ) : (
                    <button
                      type="button"
                      className="admin-btn-primary"
                      disabled={!canAfford || purchasingId === item.item_id}
                      onClick={() => handlePurchase(item)}
                    >
                      {purchasingId === item.item_id ? 'Buying…' : canAfford ? 'Buy' : 'Not enough points'}
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default Shop