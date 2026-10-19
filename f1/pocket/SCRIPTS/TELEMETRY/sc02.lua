-- SC-02 snelheidslimiet (EdgeTX telemetry screen, RadioMaster Pocket 128x64)
-- The scroll wheel P1 is mixed to CH7. Its position picks a speed limit; the car (and the sim) read CH7.
-- Shows the limit big on the screen and says it out loud when it changes.
local STEPS = { 20, 40, 60, 80, 100, 0 }      -- km/h, 0 = geen limiet (laatste stand)
local cur, pend, pendT = 0, 0, 0

local function stepOf(v)                        -- CH7 value -1024..1024 -> index 1..#STEPS
  local i = math.floor((v + 1024) * #STEPS / 2049) + 1
  if i < 1 then i = 1 end
  if i > #STEPS then i = #STEPS end
  return i
end

local function background()
  local i = stepOf(getValue("ch7"))
  if i ~= pend then pend = i; pendT = getTime() end
  if pend ~= cur and getTime() - pendT > 35 then     -- 0.35 s stable before announcing
    cur = pend
    local lim = STEPS[cur]
    if lim == 0 then playTone(900, 120, 40); playTone(1300, 160, 0)
    else playNumber(lim, UNIT_KMH) end
  end
end

local function run(event)
  background()
  lcd.clear()
  local lim = STEPS[cur ~= 0 and cur or stepOf(getValue("ch7"))]
  lcd.drawText(2, 1, "SC-02  SNELHEIDSLIMIET", SMLSIZE)
  lcd.drawLine(0, 9, LCD_W - 1, 9, SOLID, FORCE)
  if lim == 0 then
    lcd.drawText(14, 22, "GEEN", DBLSIZE)
    lcd.drawText(66, 22, "LIMIET", DBLSIZE)
  else
    lcd.drawNumber(18, 16, lim, XXLSIZE)
    lcd.drawText(84, 36, "km/h", MIDSIZE)
  end
  for k = 1, #STEPS do                             -- little scale at the bottom
    local x = 6 + (k - 1) * 22
    if k == cur then lcd.drawFilledRectangle(x, 56, 18, 6, SOLID) else lcd.drawRectangle(x, 56, 18, 6, SOLID) end
  end
  return 0
end

return { run = run, background = background }
