
Citizen.CreateThread(function()
    function Initialize(scaleform)
        scaleform = RequestScaleformMovie(scaleform)
        while not HasScaleformMovieLoaded(scaleform) do
            Citizen.Wait(0)
        end
        
        PushScaleformMovieFunction(scaleform, "SET_ICON")
        PushScaleformMovieFunctionParameterInt(100)
        PushScaleformMovieFunctionParameterInt(7)
        PushScaleformMovieFunctionParameterInt(66)
        PopScaleformMovieFunctionVoid()

        PushScaleformMovieFunction(scaleform, "SET_TITLE")
        PushScaleformMovieFunctionParameterString("Left Side Title")
        PushScaleformMovieFunctionParameterString("Right Side Title")
        PushScaleformMovieFunctionParameterInt(14)
        PopScaleformMovieFunctionVoid()

        PushScaleformMovieFunction(scaleform, "SET_DATA_SLOT")
        PushScaleformMovieFunctionParameterInt(0)
        PushScaleformMovieFunctionParameterInt(1240)
        PushScaleformMovieFunctionParameterString("Player Name")
        PushScaleformMovieFunctionParameterInt(200)
        PushScaleformMovieFunctionParameterInt(2000)
        PushScaleformMovieFunctionParameterInt(69)
        PushScaleformMovieFunctionParameterInt(14)
        PushScaleformMovieFunctionParameterString("   CTAG")
        PushScaleformMovieFunctionParameterInt(1)
        PopScaleformMovieFunctionVoid()

        PushScaleformMovieFunction(scaleform, "DISPLAY_VIEW")
        PopScaleformMovieFunctionVoid()
        
        return scaleform
    end

    local scaleform = Initialize("MP_MM_CARD_FREEMODE")
    
    while true do
        Citizen.Wait(0)
        DrawScaleformMovieFullscreen(scaleform, 255, 255, 255, 255, 0)
    end
end)
Citizen.CreateThread(function()
    function Initialize(scaleform)
        scaleform = RequestScaleformMovie(scaleform)
        while not HasScaleformMovieLoaded(scaleform) do
            Citizen.Wait(0)
        end

        PushScaleformMovieFunction(scaleform, "SET_TITLE")
        PushScaleformMovieFunctionParameterString("Title")
        PopScaleformMovieFunctionVoid()

        PushScaleformMovieFunction(scaleform, "SET_DATA_SLOT")
        PushScaleformMovieFunctionParameterInt(0) -- DATA SLOT ID, the number of the objective in the list
        PushScaleformMovieFunctionParameterInt(0) -- type = 0 is Money - 1+ check
        PushScaleformMovieFunctionParameterInt(0) -- 1+ = Star After Item Name
        PushScaleformMovieFunctionParameterInt(0) -- 1+ = shirt icon
        PushScaleformMovieFunctionParameterInt(1000) -- Cost Of Item
        PushScaleformMovieFunctionParameterString("Current Item Type") -- Name Of Item
        PopScaleformMovieFunctionVoid()

        PushScaleformMovieFunction(scaleform, "SET_DATA_SLOT")
        PushScaleformMovieFunctionParameterInt(1) -- DATA SLOT ID, the number of the objective in the list
        PushScaleformMovieFunctionParameterInt(0) -- type = 0 is Money - 1+ check
        PushScaleformMovieFunctionParameterInt(0) -- 1+ = Star After Item Name
        PushScaleformMovieFunctionParameterInt(0) -- 1+ = shirt icon
        PushScaleformMovieFunctionParameterInt(1000) -- Cost Of Item
        PushScaleformMovieFunctionParameterString("Item #2") -- Name Of Item
        PopScaleformMovieFunctionVoid()

        PushScaleformMovieFunction(scaleform, "SET_DESCRIPTION")
        PushScaleformMovieFunctionParameterString("Item Desc")
        PushScaleformMovieFunctionParameterString("Item Price")
        PushScaleformMovieFunctionParameterString("Item Value")
        PopScaleformMovieFunctionVoid()

        PushScaleformMovieFunction(scaleform, "SET_IMAGE")
        PushScaleformMovieFunctionParameterString("textureDict")
        PushScaleformMovieFunctionParameterString("textureName")
        PopScaleformMovieFunctionVoid()

        PushScaleformMovieFunction(scaleform, "DRAW_MENU_LIST")
        PopScaleformMovieFunctionVoid()
        return scaleform
    end

    scaleform = Initialize("SHOP_MENU_DLC")
    while true do
        Citizen.Wait(0)
        veh2 = GetPlayersLastVehicle()
        ped = PlayerPedId()
        x,y,z = table.unpack(GetEntityCoords(veh2, true))
        xrot,yrot,zrot = table.unpack(GetEntityRotation(veh2, 1))
        DrawScaleformMovie_3dNonAdditive(scaleform, x,y,z+1.0, 0, 0, 0, 1.0, 1.0, 1.0, 5.0, 3.0, 0, 1)
    end
end)