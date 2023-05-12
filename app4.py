from ObTypes import *
from Property import *
import Pipeline
import StreamProfile
import Device
from Error import ObException
import cv2
import numpy as np
import sys

import time

# 定义保存间隔时间
SAVE_INTERVAL = 0.5 # 每隔0.5秒保存一次
last_save_time = time.time() # 初始化上一次保存时间

q = 113
ESC = 27

D = 68
d = 100
F = 70
f = 102
S = 83
s = 115
add = 43
reduce = 45
FEMTO = 0x0635

sync	= False
started = True
hd2c	= False
sd2c	= True
alpha   = 0.5
keyRecord  = -1

saveflag = False

frameSet   = None
colorFrame = None
depthFrame = None

try:
    pipe = Pipeline.Pipeline(None, None)
    config = Pipeline.Config()

    try:
        profiles = pipe.getStreamProfileList(OB_PY_SENSOR_COLOR)
        videoProfile = None
        try:
            videoProfile = profiles.getVideoStreamProfile(640,0,OB_PY_FORMAT_RGB888,30)
        except ObException as e:
            print("function: %s\nargs: %s\nmessage: %s\ntype: %d\nstatus: %d" %(e.getName(), e.getArgs(), e.getMessage(), e.getExceptionType(), e.getStatus()))
            videoProfile = profiles.getVideoStreamProfile(640,0,OB_PY_FORMAT_UNKNOWN,30)
        colorProfile = videoProfile.toConcreteStreamProfile(OB_PY_STREAM_VIDEO)
        config.enableStream(colorProfile)
    except ObException as e:
        print("function: %s\nargs: %s\nmessage: %s\ntype: %d\nstatus: %d" %(e.getName(), e.getArgs(), e.getMessage(), e.getExceptionType(), e.getStatus()))
        print("Current device is not support color sensor!")
        sys.exit()

    try:
        profiles = pipe.getStreamProfileList(OB_PY_SENSOR_DEPTH)
        videoProfile = None
        try:
            videoProfile = profiles.getVideoStreamProfile(640,0,OB_PY_FORMAT_Y16,30)
        except ObException as e:
            print("function: %s\nargs: %s\nmessage: %s\ntype: %d\nstatus: %d" %(e.getName(), e.getArgs(), e.getMessage(), e.getExceptionType(), e.getStatus()))
            videoProfile = profiles.getVideoStreamProfile(640,0,OB_PY_FORMAT_UNKNOWN,30)
        depthProfile = videoProfile.toConcreteStreamProfile(OB_PY_STREAM_VIDEO)
        config.enableStream(depthProfile)
    except ObException as e:
        print("function: %s\nargs: %s\nmessage: %s\ntype: %d\nstatus: %d" %(e.getName(), e.getArgs(), e.getMessage(), e.getExceptionType(), e.getStatus()))
        print("Current device is not support depth sensor!")
        sys.exit()
    
    # 配置对齐模式为软件D2C对齐
    config.setAlignMode(OB_PY_ALIGN_D2C_SW_MODE)

    # # 获取镜像属性是否有可写的权限
    # if pipe.getDevice().isPropertySupported(OB_PROP_COLOR_MIRROR_BOOL, OB_PERMISSION_WRITE):
    #     # 设置镜像
    #     pipe.getDevice().setBoolProperty(OB_PROP_COLOR_MIRROR_BOOL, false)
        
    try:
        # 启动在Config中配置的流，如果不传参数，将启动默认配置启动流
        pipe.start(config, None)
    except ObException as e:
        print("function: %s\nargs: %s\nmessage: %s\ntype: %d\nstatus: %d" %(e.getName(), e.getArgs(), e.getMessage(), e.getExceptionType(), e.getStatus()))
    
    while True:
        frameSet = None
        colorFrame = None
        depthFrame = None
        key = cv2.waitKey(1)
        
        # 按+键增加alpha
        if keyRecord != key and key == add :
            alpha += 0.01
            if alpha >= 1.0 :
                alpha = 1.0

		# 按-键减少alpha
        if keyRecord != key and key == reduce :
            alpha -= 0.01
            if alpha <= 0.0 :
                alpha = 0.0

        # 按D键开关软件D2C
        if keyRecord != key and (key == D or key == d) :
            try:
                if sd2c == False:
                    started = False
                    pipe.stop()
                    sd2c= True
                    hd2c = False
                    config.setAlignMode(OB_PY_ALIGN_D2C_SW_MODE)
                    pipe.start(config, None)
                    started = True
                else:
                    started = False
                    pipe.stop()
                    hd2c = False
                    sd2c = False
                    config.setAlignMode(OB_PY_ALIGN_DISABLE)
                    pipe.start(config, None)
                    started = True
            except ObException as e:
                print("function: %s\nargs: %s\nmessage: %s\ntype: %d\nstatus: %d" %(e.getName(), e.getArgs(), e.getMessage(), e.getExceptionType(), e.getStatus()))
                print("Property not support")
        
        keyRecord = key

		# 以阻塞的方式等待一帧数据，该帧是一个复合帧，里面包含配置里启用的所有流的帧数据，
		# 并设置帧的等待超时时间为100ms
        frameSet = pipe.waitForFrames(100)

        if frameSet == None:
            continue
        else:
            # 在窗口中渲染一组帧数据，这里将渲染彩色帧及深度帧，将彩色帧及深度帧叠加显示
            colorFrame = frameSet.colorFrame()
            depthFrame = frameSet.depthFrame()

            if colorFrame != None and depthFrame != None:
    			# 获取帧的大小、数据、宽高
                colorSize = colorFrame.dataSize()
                colorData = colorFrame.data()
                depthSize = depthFrame.dataSize()
                depthData = depthFrame.data()
                colorWidth = colorFrame.width()
                colorHeight = colorFrame.height()
                depthWidth = depthFrame.width()
                depthHeight = depthFrame.height()
                if colorSize !=0 and depthSize !=0 :
                    newColorData = colorData
					# 将彩色帧数据大小调整为(height,width,3)
                    newColorData.resize((colorHeight, colorWidth, 3))
					# 将彩色帧数据BGR转RGB
                    newColorData = cv2.cvtColor(newColorData, cv2.COLOR_BGR2RGB) 

					# 将深度帧数据大小调整为(height,width,2)
                    depthData = np.resize(depthData,(colorHeight, colorWidth, 2))
					# 分辨率不一致，多余的部分填0
                    if colorHeight != depthHeight:
                        depthData[depthHeight:colorHeight-1,:]=0

					# 将深度帧数据8bit转16bit
                    newDepthData = depthData[:,:,0]+depthData[:,:,1]*256
					# 将深度帧数据16bit转8bit，用于渲染
                    newDepthData = newDepthData.astype(np.uint8)
					# 将深度帧数据GRAY转RGB
                    newDepthData = cv2.cvtColor(newDepthData, cv2.COLOR_GRAY2RGB) 

					# 将彩色帧及深度帧叠加显示
                    newDatas = cv2.addWeighted(newColorData, (1 - alpha), newDepthData, alpha, 0)

					# 创建窗口
                    cv2.namedWindow("SyncAlignViewer", cv2.WINDOW_NORMAL)

					# 显示图像
                    cv2.imshow("SyncAlignViewer", newDatas)

					# 按 ESC 或 'q' 关闭窗口
                    if key == ESC or key == q:
                        cv2.destroyAllWindows()
                        break

                    if key == S or key == s:
                        current_time = time.time()
                        if current_time - last_save_time >= SAVE_INTERVAL:
                            # 保存深度图
                            depthRawName = "images/raw/" + "depth_" + str(depthFrame.timeStamp()) + ".raw"
                            depthPngName = "images/png/" + "depth_" + str(depthFrame.timeStamp()) + ".png"
                            data = depthFrame.data()
                            # 保存深度图原始数据为raw格式
                            data.tofile(depthRawName)
                            # 将帧数据大小调整为(height,width,2)
                            data.resize((depthFrame.height(), depthFrame.width(), 2))
                            # 将帧数据8bit转16bit
                            newData = data[:,:,0]+data[:,:,1]*256
                            # 将帧数据16bit转8bit，用于渲染
                            newData = newData.astype(np.uint8)
                            # 将帧数据GRAY转RGB
                            newData = cv2.cvtColor(newData, cv2.COLOR_GRAY2RGB) 
                            # 保存深度图为png格式
                            cv2.imwrite(depthPngName, newData)

                            # 保存彩色图
                            colorRawName = "images/raw/" + "color_" + str(colorFrame.timeStamp()) + ".raw"
                            colorPngName = "images/png/" + "color_" + str(colorFrame.timeStamp()) + ".png"
                            data = colorFrame.data()
                            # # 保存彩色图原始数据为raw格式
                            data.tofile(colorRawName)
                            newData = data
                            # 将帧数据大小调整为(height,width,3)
                            newData.resize((colorFrame.height(), colorFrame.width(), 3))
                            # 将帧数据BGR转RGB
                            newData = cv2.cvtColor(newData, cv2.COLOR_BGR2RGB) 
                            # 保存彩色图为png格式
                            cv2.imwrite(colorPngName,newData)

                            # 更新上一次保存时间
                            last_save_time = current_time

                    keyRecord = key

    # 停止Pipeline，将不再产生帧数据
    pipe.stop()

except ObException as e:
    print("function: %s\nargs: %s\nmessage: %s\ntype: %d\nstatus: %d" %(e.getName(), e.getArgs(), e.getMessage(), e.getExceptionType(), e.getStatus()))