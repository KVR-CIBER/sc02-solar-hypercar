-- SC-02 snelheid + snelheidslimiet (EdgeTX telemetry screen, RadioMaster Pocket 128x64)
-- The scroll wheel P1 is mixed to CH7. Its position picks a speed limit; the car (and the sim) read CH7.
-- Left: real speed from the car over ELRS/CRSF telemetry. The car's ESP32-S3 sends its hall-sensor speed as a
-- CRSF GPS frame (0x02, groundspeed in 0.1 km/h); EdgeTX discovers that as sensor "GSpd" in km/h.
-- Right: the limit, said out loud when it changes.
-- Browser sim over one USB cable: with USB mode "Serial (VCP)" and the VCP port set to LUA, the channels go out as
-- "C,ch1,...,ch8" lines (pocket_bridge.py turns them into the sim's joystick) and the sim speed comes back as "S<km/h>".
-- In a model whose name contains "SIM" (model "SC02 SIM": RF off, USB joystick) it shows SIM instead of the speed.
local STEPS = { 20, 40, 60, 80, 100, 0 }      -- km/h, 0 = geen limiet (laatste stand)
local SPEED_SENSOR = "GSpd"
local cur, pend, pendT = 0, 0, 0
local sim = false
local simKmh, simT, rx = 0, -1000, ""             -- last speed from the browser sim and when it came (10 ms ticks)
local speedId                                   -- field id of GSpd, nil until the sensor has been discovered

local function stepOf(v)                        -- CH7 value -1024..1024 -> index 1..#STEPS
  local i = math.floor((v + 1024) * #STEPS / 2049) + 1
  if i < 1 then i = 1 end
  if i > #STEPS then i = #STEPS end
  return i
end

local function init()
  local info = model.getInfo()
  sim = info ~= nil and string.find(string.upper(info.name or ""), "SIM") ~= nil
end

local function serialLink()                     -- no-op unless the USB/VCP port is in LUA mode
  if not serialWrite then return end
  local c = {}
  for k = 1, 8 do c[k] = math.floor(getValue("ch" .. k) or 0) end
  serialWrite(string.format("C,%d,%d,%d,%d,%d,%d,%d,%d\n", c[1], c[2], c[3], c[4], c[5], c[6], c[7], c[8]))
  rx = rx .. (serialRead(64) or "")
  for v in string.gmatch(rx, "S(%-?%d+)\n") do simKmh = tonumber(v); simT = getTime() end
  rx = string.match(rx, "[^\n]*$")              -- keep only an unfinished line
  if #rx > 200 then rx = "" end
end

local function background()
  serialLink()
  local i = stepOf(getValue("ch7"))
  if i ~= pend then pend = i; pendT = getTime() end
  if pend ~= cur and getTime() - pendT > 35 then     -- 0.35 s stable before announcing
    cur = pend
    local lim = STEPS[cur]
    if lim == 0 then playTone(900, 120, 40); playTone(1300, 160, 0)
    else playNumber(lim, UNIT_KMH) end
  end
end

local function speed()                          -- km/h, or nil when there is no live telemetry speed
  if not speedId then
    local f = getFieldInfo(SPEED_SENSOR)
    if not f then return nil end
    speedId = f.id
  end
  if getRSSI() == 0 then return nil end          -- link lost: the last value would be stale
  return getValue(speedId)
end

local function run(event)
  background()
  local simLive = getTime() - simT < 100
  lcd.clear()
  local lim = STEPS[cur ~= 0 and cur or stepOf(getValue("ch7"))]

  lcd.drawText(1, 1, "SC-02", SMLSIZE)
  lcd.drawLine(0, 9, LCD_W - 1, 9, SOLID, FORCE)
  lcd.drawLine(80, 10, 80, 53, SOLID, FORCE)

  -- left: speed
  if simLive then
    lcd.drawText(LCD_W - 1, 1, "SIM", SMLSIZE + RIGHT + INVERS)
    local over = lim ~= 0 and simKmh > lim
    lcd.drawNumber(2, 13, simKmh, XXLSIZE + ((over and getTime() % 50 < 25) and INVERS or 0))
    lcd.drawText(58, 46, "km/h", SMLSIZE)
  elseif sim then
    lcd.drawText(LCD_W - 1, 1, "SIM  USB-JOYSTICK", SMLSIZE + RIGHT + INVERS)
    lcd.drawText(20, 20, "SIM", DBLSIZE)
  else
    local v = speed()
    if v then
      lcd.drawText(LCD_W - 1, 1, "LIVE", SMLSIZE + RIGHT)
      local kmh = math.floor(v + 0.5)
      local over = lim ~= 0 and kmh > lim
      lcd.drawNumber(2, 13, kmh, XXLSIZE + ((over and getTime() % 50 < 25) and INVERS or 0))
    else
      lcd.drawText(LCD_W - 1, 1, "GEEN TELEMETRIE", SMLSIZE + RIGHT + BLINK)
      lcd.drawText(24, 22, "--", DBLSIZE)
    end
    lcd.drawText(58, 46, "km/h", SMLSIZE)
  end

  -- right: limit
  lcd.drawText(84, 12, "LIMIET", SMLSIZE)
  if lim == 0 then
    lcd.drawText(84, 24, "GEEN", MIDSIZE)
  else
    lcd.drawNumber(84, 22, lim, DBLSIZE)
    lcd.drawText(84, 40, "km/h", SMLSIZE)
  end

  for k = 1, #STEPS do                             -- little scale at the bottom
    local x = 1 + (k - 1) * 21
    if k == cur then lcd.drawFilledRectangle(x, 56, 17, 6, SOLID) else lcd.drawRectangle(x, 56, 17, 6, SOLID) end
  end
  return 0
end

return { init = init, run = run, background = background }
