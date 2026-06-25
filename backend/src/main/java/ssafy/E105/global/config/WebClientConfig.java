package ssafy.E105.global.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;
import reactor.netty.resources.ConnectionProvider;

import java.time.Duration;

@Configuration
public class WebClientConfig {

    private static final int FASTAPI_MAX_CONNECTIONS = 200;
    private static final int FASTAPI_PENDING_ACQUIRE_TIMEOUT_SECONDS = 30;
    private static final int FASTAPI_MAX_IDLE_TIME_SECONDS = 30;
    private static final int FASTAPI_RESPONSE_TIMEOUT_SECONDS = 180;

    @Bean
    public WebClient webClient() {
        ConnectionProvider connectionProvider = ConnectionProvider.builder("fastapi-webclient")
                .maxConnections(FASTAPI_MAX_CONNECTIONS)
                .pendingAcquireTimeout(Duration.ofSeconds(FASTAPI_PENDING_ACQUIRE_TIMEOUT_SECONDS))
                .maxIdleTime(Duration.ofSeconds(FASTAPI_MAX_IDLE_TIME_SECONDS))
                .build();

        HttpClient httpClient = HttpClient.create(connectionProvider)
                .responseTimeout(Duration.ofSeconds(FASTAPI_RESPONSE_TIMEOUT_SECONDS));

        return WebClient.builder()
                .clientConnector(new ReactorClientHttpConnector(httpClient))
                .build();
    }
}
