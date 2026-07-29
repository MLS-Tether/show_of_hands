import './CharacterAvatar.css'

function CharacterAvatar({ avatarBase, avatarAccessory, badges = [], size }) {
  const rootClassName = size === 'sm' ? 'character-avatar character-avatar-sm' : 'character-avatar'

  return (
    <div className={rootClassName}>
      <div className="character-avatar-stage">
        {avatarBase ? (
          <img
            src={avatarBase.image_url}
            alt={avatarBase.name}
            className="character-avatar-layer character-avatar-base"
          />
        ) : (
          <div className="character-avatar-placeholder">?</div>
        )}
        {avatarAccessory && (
          <img
            src={avatarAccessory.image_url}
            alt={avatarAccessory.name}
            className="character-avatar-layer character-avatar-accessory"
          />
        )}
      </div>

      {badges.length > 0 && (
        <div className="character-avatar-badges">
          {badges.map((badge) => (
            <img
              key={badge.item_id}
              src={badge.image_url}
              alt={badge.name}
              title={badge.name}
              className="character-avatar-badge"
            />
          ))}
        </div>
      )}
    </div>
  )
}

export default CharacterAvatar