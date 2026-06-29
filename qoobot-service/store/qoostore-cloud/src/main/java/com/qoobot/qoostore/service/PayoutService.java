package com.qoobot.qoostore.service;

import com.qoobot.qoostore.entity.DeveloperRevenue;
import com.qoobot.qoostore.entity.DeveloperPayout;
import com.qoobot.qoostore.repository.DeveloperPayoutRepository;
import com.qoobot.qoostore.repository.DeveloperRevenueRepository;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class PayoutService {

    private final DeveloperRevenueRepository revenueRepository;
    private final DeveloperPayoutRepository payoutRepository;

    @Transactional
    public DeveloperPayout createPayout(Long developerId, String payoutMethod) {
        LocalDate now = LocalDate.now();
        LocalDate periodStart = now.withDayOfMonth(1);
        LocalDate periodEnd = now.withDayOfMonth(now.lengthOfMonth());

        List<DeveloperRevenue> revenues = revenueRepository
                .findByDeveloperIdAndCreatedAtBetween(developerId,
                        periodStart.atStartOfDay(), periodEnd.plusDays(1).atStartOfDay());

        BigDecimal totalAmount = revenues.stream()
                .map(DeveloperRevenue::getDeveloperShare)
                .reduce(BigDecimal.ZERO, BigDecimal::add);

        if (totalAmount.compareTo(BigDecimal.ZERO) <= 0) {
            throw new RuntimeException("No revenue to payout for this period");
        }

        DeveloperPayout payout = DeveloperPayout.builder()
                .developerId(developerId)
                .amount(totalAmount)
                .periodStart(periodStart)
                .periodEnd(periodEnd)
                .status("pending")
                .payoutMethod(payoutMethod)
                .build();
        payout = payoutRepository.save(payout);

        log.info("Payout created: developerId={}, amount={}, period={}-{}",
                developerId, totalAmount, periodStart, periodEnd);
        return payout;
    }

    public List<DeveloperPayout> getPayouts(Long developerId) {
        return payoutRepository.findByDeveloperIdOrderByCreatedAtDesc(developerId);
    }

    @Transactional
    public void processPayout(Long payoutId, String transactionId) {
        DeveloperPayout payout = payoutRepository.findById(payoutId)
                .orElseThrow(() -> new RuntimeException("Payout not found: " + payoutId));
        payout.setStatus("completed");
        payout.setTransactionId(transactionId);
        payoutRepository.save(payout);
        log.info("Payout processed: payoutId={}, transactionId={}", payoutId, transactionId);
    }
}
