#include <gtest/gtest.h>
#include "qoosvc/common/result.h"

using namespace qoosvc;

TEST(ResultTest, OkValue) {
    auto r = Result<int>::ok(42);
    EXPECT_TRUE(r.is_ok());
    EXPECT_FALSE(r.is_err());
    EXPECT_EQ(r.value(), 42);
    EXPECT_EQ(*r, 42);
}

TEST(ResultTest, ErrValue) {
    auto r = Result<int>::err(ErrorCode::UNKNOWN);
    EXPECT_FALSE(r.is_ok());
    EXPECT_TRUE(r.is_err());
    EXPECT_EQ(r.error_code(), ErrorCode::UNKNOWN);
}

TEST(ResultTest, ErrWithMessage) {
    auto r = Result<int>::err(ErrorCode::INVALID_ARGUMENT, "Bad input");
    EXPECT_TRUE(r.is_err());
    EXPECT_EQ(r.error_message(), "Bad input");
}

TEST(ResultTest, UnwrapOr) {
    auto ok = Result<int>::ok(10);
    EXPECT_EQ(ok.unwrap_or(0), 10);

    auto err = Result<int>::err(ErrorCode::UNKNOWN);
    EXPECT_EQ(err.unwrap_or(99), 99);
}

TEST(ResultTest, VoidOk) {
    auto r = Result<void>::ok();
    EXPECT_TRUE(r.is_ok());
    EXPECT_FALSE(r.is_err());
}

TEST(ResultTest, VoidErr) {
    auto r = Result<void>::err(ErrorCode::TIMEOUT, "Timed out");
    EXPECT_TRUE(r.is_err());
    EXPECT_EQ(r.error_code(), ErrorCode::TIMEOUT);
    EXPECT_EQ(r.error_message(), "Timed out");
}

TEST(ResultTest, ArrowOperator) {
    struct Foo { int x = 5; };
    auto r = Result<Foo>::ok(Foo{});
    EXPECT_EQ(r->x, 5);
}

TEST(ResultTest, ConstAccess) {
    const auto r = Result<int>::ok(100);
    EXPECT_EQ(r.value(), 100);
    EXPECT_EQ(*r, 100);
}
