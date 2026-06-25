package ssafy.E105.global.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;

import java.util.concurrent.Executor;

@Configuration
public class AsyncExecutorConfig {

    private static final int CHAT_RECOMMEND_CORE_POOL_SIZE = 8;
    private static final int CHAT_RECOMMEND_MAX_POOL_SIZE = 16;
    private static final int CHAT_RECOMMEND_QUEUE_CAPACITY = 300;
    private static final String CHAT_RECOMMEND_THREAD_NAME_PREFIX = "chat-recommend-";

    @Bean(name = "chatRecommendationExecutor")
    public Executor chatRecommendationExecutor() {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(CHAT_RECOMMEND_CORE_POOL_SIZE);
        executor.setMaxPoolSize(CHAT_RECOMMEND_MAX_POOL_SIZE);
        executor.setQueueCapacity(CHAT_RECOMMEND_QUEUE_CAPACITY);
        executor.setThreadNamePrefix(CHAT_RECOMMEND_THREAD_NAME_PREFIX);
        executor.initialize();
        return executor;
    }
}
