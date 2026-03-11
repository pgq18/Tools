#include <unitree/robot/go2/video/video_client.hpp>
#include <iostream>
#include <fstream>
#include <ctime>

using namespace unitree::robot;


extern "C" void hello_world() {
     printf("Hello world!\n");
}

extern "C" int add(int a, int b) {
     return a + b;
}

extern "C" char* test_str(char* str) {
     return str;
}

extern "C" int test_vector(uint8_t* image_ptr) {
     std::vector<uint8_t> image_data = {1, 2, 3, 4, 5};
     memcpy(image_ptr, image_data.data(), image_data.size());
     return image_data.size();
}

extern "C" go2::VideoClient* init_camera(char* networkInterface) {
     ChannelFactory::Instance()->Init(0, networkInterface);
     static go2::VideoClient video_client;
     video_client.SetTimeout(1.0f);
     video_client.Init();

     return &video_client;
}

extern "C" int capture_img(go2::VideoClient* video_client, uint8_t* image_ptr) {
     std::vector<uint8_t> image_data;
     int ret;
     ret = video_client->GetImageSample(image_data);
     if (ret == 0) { 
          memcpy(image_ptr, image_data.data(), image_data.size());
          return image_data.size();
     }
     else {
          return -1;
     }
}
