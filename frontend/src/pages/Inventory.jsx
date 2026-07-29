import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import api from '../api'
import { useToast } from '../components/ToastContext'
import { keys, useInventory } from '../queries'
import { getUserId } from '../utils/auth'
import '../styles/shared-ui.css'
import './Inventory.css'

const CUSTOMIZE_GROUPS = [
  { key: 'avatar_base', label: 'Avatar' },
  { key: 'avatar_accessory', label: 'Accessory' },
  { key: 'badge', label: 'Badges' },
  { key: 'theme', label: 'Theme' },
]

function Inventory() {
  const userId = getUserId()
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [pendingId, setPendingId] = useState(null)

  const { data: inventory = [] } = useInventory(userId)

  async function handleToggle(row) {
    setPendingId(row.inventory_id)
    try {
      await api.patch(`/inventory/${row.inventory_id}/equip`, { equipped: !row.is_equipped })
      queryClient.invalidateQueries({ queryKey: keys.inventory(userId) })
    } catch (err) {
      showToast(err.response?.data?.message || 'Could not update equipped items.')
    } finally {
      setPendingId(null)
    }
  }

  const groupsWithItems = CUSTOMIZE_GROUPS.map((group) => ({
    ...group,
    rows: inventory.filter((row) => row.item.item_type === group.key),
  })).filter((group) => group.rows.length > 0)

  return (
    <section className="admin-page">
      <h1 className="admin-page-h1">Inventory</h1>

      {groupsWithItems.length === 0 && (
        <p className="admin-empty-card">
          No items owned yet — visit the <a href="/shop">shop</a>!
        </p>
      )}

      {groupsWithItems.map((group) => (
        <div className="customize-group" key={group.key}>
          <div className="widget-label">{group.label}</div>
          <div className="customize-group-items">
            {group.rows.map((row) => (
              <button
                type="button"
                key={row.inventory_id}
                className={`customize-item${row.is_equipped ? ' equipped' : ''}`}
                disabled={pendingId === row.inventory_id}
                onClick={() => handleToggle(row)}
              >
                <img src={row.item.image_url} alt="" />
                <span>{row.item.name}</span>
                {row.is_equipped && <span className="customize-item-badge">Equipped</span>}
              </button>
            ))}
          </div>
        </div>
      ))}
    </section>
  )
}

export default Inventory
