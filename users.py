@user_router.message(F.text == "👤 Профиль")
async def profile(message: types.Message):
    u = await get_user_data(message.from_user.id)
    if not u: 
        return await message.answer("Сначала пройди регистрацию через /start")
    
    is_admin = (message.from_user.id == ADMIN_ID)
    
    # Безопасные лимиты
    ai_lim = "∞" if is_admin else u.get('limits_ai', 0)
    search_lim = "∞" if is_admin else u.get('limits_search', 0)
    
    # Безопасная шкала опыта (10 делений)
    current_exp = u.get('exp', 0)
    filled = min(int(current_exp // 40), 10) # 400 опыта / 40 = 10 делений
    progress_bar = "🔵" * filled + "⚪️" * (10 - filled)
    
    text = (
        f"👤 **Профиль: {u.get('name', 'Странник')}**\n"
        f"🗓 В игре с: `{u.get('reg_date', '---')}`\n"
        f"🎖 Уровень: `{u.get('level', 'Новичок')}`\n"
        f"✨ Опыт: `{current_exp}`/400\n"
        f"{progress_bar}\n\n"
        f"🔮 Гадания: **{ai_lim}**\n"
        f"🤝 Поиски: **{search_lim}**"
    )
    await message.answer(text, parse_mode="Markdown")